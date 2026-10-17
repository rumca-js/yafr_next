"""
Source Service Implementation for YAFR.

Coordinates source lifecycle operations, single and batch fetching,
operational hash checking (page_hash, body_hash), feed entry extraction
into linkdatamodel, consecutive error tracking, and progress polling status.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import sys
import threading
from typing import Any, Dict, List, Optional
import warnings
from bs4 import MarkupResemblesLocatorWarning
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import webtoolkit
from linkarchivetools.model.definitions import (
    LinkDataModel,
    SourceOperationalData,
    SourcesTable,
)
from yafr.db.session import get_session, session_scope
from yafr.db.source_repository import SourceRepository
from yafr.services.entry_builder import EntryBuilder
from yafr.services.webtools_service import WebToolsWrapper

logger = logging.getLogger(__name__)

# Suppress BeautifulSoup markup locator warning
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# Apply webtoolkit email reader import bug workaround (ARCHITECTURE.md section 3.4)
if "webtoolkit.utils" in sys.modules and "utils" not in sys.modules:
    sys.modules["utils"] = sys.modules["webtoolkit.utils"]
elif hasattr(webtoolkit, "utils") and "utils" not in sys.modules:
    sys.modules["utils"] = webtoolkit.utils


class SourceService:
    """
    Service coordinating source operations, feed fetching, and background batch updates.
    """

    _lock = threading.Lock()
    _refresh_state: Dict[str, Any] = {
        "is_running": False,
        "total_sources": 0,
        "completed_sources": 0,
        "current_source_title": "",
        "percentage": 0.0,
        "errors_encountered": 0,
    }

    @classmethod
    def get_refresh_status(cls) -> Dict[str, Any]:
        """
        Returns a thread-safe snapshot of the current batch refresh progress.
        """
        with cls._lock:
            return dict(cls._refresh_state)

    @classmethod
    def start_batch_refresh(
        cls,
        source_ids: Optional[List[int]] = None,
        include_errors: bool = True,
    ) -> int:
        """
        Initiates a background thread to refresh outdated or error sources.

        :param source_ids: Specific list of source IDs (if None, all outdated)
        :param include_errors: Whether to also include sources with consecutive errors
        :return: Count of queued sources
        """
        with cls._lock:
            if cls._refresh_state["is_running"]:
                return cls._refresh_state["total_sources"]

        session = get_session()
        source_repo = SourceRepository(session)

        target_ids: List[int] = []
        if source_ids:
            target_ids = list(source_ids)
        else:
            # Query enabled outdated sources
            outdated = source_repo.get_outdated_sources(max_age_seconds=3600)
            target_ids = [s.id for s in outdated]

            if include_errors:
                # Add sources with consecutive errors
                stmt = (
                    select(SourcesTable.id)
                    .join(
                        SourceOperationalData,
                        SourcesTable.id == SourceOperationalData.source_id,
                    )
                    .where(SourcesTable.enabled == True)
                    .where(SourceOperationalData.consecutive_errors > 0)
                )
                error_ids = list(session.execute(stmt).scalars().all())
                for eid in error_ids:
                    if eid not in target_ids:
                        target_ids.append(eid)

        if not target_ids:
            return 0

        with cls._lock:
            cls._refresh_state = {
                "is_running": True,
                "total_sources": len(target_ids),
                "completed_sources": 0,
                "current_source_title": "Starting batch refresh...",
                "percentage": 0.0,
                "errors_encountered": 0,
            }

        worker_thread = threading.Thread(
            target=cls._run_batch_worker,
            args=(target_ids,),
            daemon=True,
            name="SourceBatchRefresher",
        )
        worker_thread.start()
        return len(target_ids)

    @classmethod
    def _run_batch_worker(cls, target_ids: List[int]) -> None:
        """
        Background worker thread executing sequential source fetches.
        """
        total = len(target_ids)
        completed = 0
        errors = 0

        for s_id in target_ids:
            source_title = f"Source #{s_id}"
            try:
                with session_scope() as session:
                    source = session.get(SourcesTable, s_id)
                    if source:
                        source_title = source.title or source.url

                with cls._lock:
                    cls._refresh_state["current_source_title"] = source_title

                res = cls.fetch_source(s_id)
                if not res.get("success"):
                    errors += 1
            except Exception as err:
                logger.error("Batch worker error fetching source %s: %s", s_id, err)
                errors += 1

            completed += 1
            with cls._lock:
                cls._refresh_state["completed_sources"] = completed
                cls._refresh_state["errors_encountered"] = errors
                cls._refresh_state["percentage"] = round((completed / total) * 100.0, 1)

        with cls._lock:
            cls._refresh_state["is_running"] = False
            cls._refresh_state["current_source_title"] = "Batch refresh finished."

    @classmethod
    def fetch_source(
        cls,
        source_id: int,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Fetches a single source from the internet, verifies hashes, extracts feed entries,
        and persists new LinkDataModel records.

        :param source_id: ID of the source to refresh
        :param session: Optional active database session
        :return: Result dictionary with success, message, status, entries_added
        """
        if session is not None:
            return cls._execute_fetch(source_id, session)
        else:
            with session_scope() as scoped_session:
                return cls._execute_fetch(source_id, scoped_session)

    @classmethod
    def _execute_fetch(cls, source_id: int, session: Session) -> Dict[str, Any]:
        source = session.get(SourcesTable, source_id)
        if not source:
            return {
                "success": False,
                "source_id": source_id,
                "error": "Source not found",
                "status": "error",
            }

        op_data = (
            session.execute(
                select(SourceOperationalData).where(
                    SourceOperationalData.source_id == source_id
                )
            )
            .scalars()
            .first()
        )

        if op_data is None:
            op_data = SourceOperationalData(
                source_id=source_id,
                consecutive_errors=0,
                number_of_entries=0,
            )
            session.add(op_data)
            session.flush()

        # Download content using WebToolsWrapper (BaseUrl / RemoteUrl)
        try:
            web_client = WebToolsWrapper(url=source.url, session=session, timeout_s=15)
            response = web_client.get_response()
            if response is None:
                raise ConnectionError(
                    f"Failed to fetch content from {source.url} (no response received)"
                )

            if not response.is_valid():
                status = response.get_status_code()
                err_detail = (
                    "; ".join(response.errors)
                    if getattr(response, "errors", None)
                    else ""
                )
                raise ConnectionError(
                    f"HTTP status {status} when fetching {source.url}"
                    + (f": {err_detail}" if err_detail else "")
                )

            content_str = web_client.get_text()
            if content_str is None:
                raise ValueError(f"No text content returned for source {source.url}")

            content_binary = response.get_binary()
            if content_binary is not None:
                content_bytes = content_binary
            else:
                content_bytes = content_str.encode("utf-8", errors="replace")

        except Exception as err:
            logger.warning(
                "Failed to fetch source %s (%s): %s", source_id, source.url, err
            )
            op_data.consecutive_errors = (op_data.consecutive_errors or 0) + 1
            op_data.date_fetched = datetime.now(timezone.utc)
            session.commit()
            return {
                "success": False,
                "source_id": source_id,
                "error": f"Network download error: {err}",
                "status": "error",
            }

        # Calculate hashes
        page_hash = hashlib.sha256(content_bytes).digest()
        body_hash = page_hash

        # Check for operational hash equality
        if op_data.page_hash and op_data.page_hash == page_hash:
            logger.info(
                "Source %s (%s) hash unchanged, skipping entry parse",
                source_id,
                source.title,
            )
            op_data.date_fetched = datetime.now(timezone.utc)
            op_data.date_successful_fetch = datetime.now(timezone.utc)
            op_data.consecutive_errors = 0
            session.commit()
            return {
                "success": True,
                "source_id": source_id,
                "status": "unchanged",
                "message": "Content unchanged (hash match).",
                "entries_added": 0,
            }

        # Parse RSS / Feed entries
        try:
            rss_page = webtoolkit.RssPage(source.url, content_str)
            raw_entries = list(rss_page.get_entries()) if rss_page.is_valid() else []
            if not raw_entries and hasattr(web_client, "get_entries"):
                raw_entries = web_client.get_entries() or []
        except Exception as err:
            logger.warning("Error parsing RSS feed for source %s: %s", source_id, err)
            op_data.consecutive_errors = (op_data.consecutive_errors or 0) + 1
            op_data.date_fetched = datetime.now(timezone.utc)
            session.commit()
            return {
                "success": False,
                "source_id": source_id,
                "error": f"Feed parsing error: {err}",
                "status": "error",
            }

        builder = EntryBuilder(session=session)
        entries_added = 0

        for item in raw_entries:
            link = (item.get("link") or "").strip()
            if not link:
                continue

            title = item.get("title")
            desc = item.get("description")
            thumb = item.get("thumbnail")
            author = item.get("author")
            album = item.get("album")
            lang = item.get("language")
            date_published = item.get("date_published")
            tags = item.get("tags") if isinstance(item.get("tags"), list) else None

            created_entry = builder.build_and_save(
                link=link,
                title=title,
                description=desc,
                source=source,
                thumbnail=thumb,
                author=author,
                album=album,
                language=lang,
                date_published=date_published,
                tags=tags,
                commit=False,
            )
            if created_entry is not None:
                entries_added += 1

        session.flush()

        # Update operational metrics
        total_source_entries = (
            session.execute(
                select(func.count(LinkDataModel.id)).where(
                    LinkDataModel.source_id == source.id
                )
            ).scalar()
            or 0
        )

        now_utc = datetime.now(timezone.utc)
        op_data.page_hash = page_hash
        op_data.body_hash = body_hash
        op_data.number_of_entries = total_source_entries
        op_data.consecutive_errors = 0
        op_data.date_fetched = now_utc
        op_data.date_successful_fetch = now_utc

        session.commit()

        return {
            "success": True,
            "source_id": source_id,
            "status": "completed",
            "message": f"Successfully refreshed {source.title}: {entries_added} new entries added.",
            "entries_added": entries_added,
        }

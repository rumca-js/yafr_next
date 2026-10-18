"""
Link Background Jobs Handlers for YAFR.

Contains handlers for link-related tasks, including JOB_LINK_UPDATE_DATA ('link-update-data').
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import BackgroundJob, LinkDataModel
from yafr.db.entry_repository import EntryRepository
from yafr.services.webtools_service import WebToolsWrapper
from yafr.workers.jobs.base import BaseJobHandler

logger = logging.getLogger(__name__)

JOB_LINK_UPDATE_DATA = "link-update-data"
JOB_LINK_DOWNLOAD_SOCIAL = "link-download-social"


class LinkUpdateDataJobHandler(BaseJobHandler):
    """
    Handler for JOB_LINK_UPDATE_DATA ('link-update-data').

    Refreshes link metadata by obtaining a webtoolkit URL handler (BaseUrl or RemoteUrl)
    via WebToolsWrapper, extracting get_title(), get_description(), get_date_published(),
    get_author(), get_language(), get_thumbnail(), etc. directly via webtoolkit without
    raw response or BeautifulSoup HTML parsing fallbacks.
    """

    job_types = (JOB_LINK_UPDATE_DATA, "JOB_LINK_UPDATE_DATA")

    def execute(self, job: BackgroundJob, session: Session) -> Dict[str, Any]:
        """
        Executes link metadata update for the target entry.

        :param job: BackgroundJob record
        :param session: Active database session
        :return: Execution result dictionary
        """
        subject = (job.subject or "").strip()
        entry_repo = EntryRepository(session)
        entry: Optional[LinkDataModel] = None

        if subject.isdigit():
            entry = entry_repo.get_by_id(int(subject))
        elif subject:
            entry = entry_repo.get_by_link(subject)

        if not entry:
            return {
                "success": False,
                "status": "error",
                "error": f"Entry not found for subject: '{subject}'",
            }

        if not entry.link:
            return {
                "success": False,
                "status": "error",
                "error": f"Entry #{entry.id} has no link URL",
            }

        try:
            # Obtain Url handler via WebToolsWrapper (either BaseUrl or RemoteUrl)
            web_client = WebToolsWrapper(url=entry.link, session=session, timeout_s=15)
            url_handler = getattr(web_client, "url_handler", None)

            response = web_client.get_response()
            if response is None:
                if not entry.date_dead_since:
                    entry.date_dead_since = datetime.now(timezone.utc)
                entry.date_update_last = datetime.now(timezone.utc)
                session.commit()
                return {
                    "success": False,
                    "status": "error",
                    "error": f"Failed to fetch content from {entry.link}",
                }

            if hasattr(web_client, "is_valid") and not web_client.is_valid():
                if not entry.date_dead_since:
                    entry.date_dead_since = datetime.now(timezone.utc)
            else:
                entry.date_dead_since = None

            # Fetch BaseUrl / RemoteUrl metadata directly via webtoolkit
            title = web_client.get_title() if hasattr(web_client, "get_title") else None
            if not title and url_handler and hasattr(url_handler, "get_title"):
                title = url_handler.get_title()

            description = (
                web_client.get_description()
                if hasattr(web_client, "get_description")
                else None
            )
            if not description and url_handler and hasattr(url_handler, "get_description"):
                description = url_handler.get_description()

            date_published = (
                web_client.get_date_published()
                if hasattr(web_client, "get_date_published")
                else None
            )
            if not date_published and url_handler and hasattr(url_handler, "get_date_published"):
                date_published = url_handler.get_date_published()

            author = web_client.get_author() if hasattr(web_client, "get_author") else None
            if not author and url_handler and hasattr(url_handler, "get_author"):
                author = url_handler.get_author()

            album = web_client.get_album() if hasattr(web_client, "get_album") else None
            if not album and url_handler and hasattr(url_handler, "get_album"):
                album = url_handler.get_album()

            language = (
                web_client.get_language()
                if hasattr(web_client, "get_language")
                else None
            )
            if not language and url_handler and hasattr(url_handler, "get_language"):
                language = url_handler.get_language()

            thumbnail = (
                web_client.get_thumbnail()
                if hasattr(web_client, "get_thumbnail")
                else None
            )
            if not thumbnail and url_handler and hasattr(url_handler, "get_thumbnail"):
                thumbnail = url_handler.get_thumbnail()

            status_code = (
                web_client.get_status_code()
                if hasattr(web_client, "get_status_code")
                else None
            )

            # Update entry properties
            if title and str(title).strip():
                entry.title = str(title).strip()
            if description and str(description).strip():
                entry.description = str(description).strip()
            if date_published:
                if isinstance(date_published, str) and date_published.strip():
                    try:
                        entry.date_published = datetime.fromisoformat(date_published.strip())
                    except Exception:
                        pass
                elif isinstance(date_published, datetime):
                    entry.date_published = date_published
            if author and str(author).strip():
                entry.author = str(author).strip()
            if album and str(album).strip():
                entry.album = str(album).strip()
            if language and str(language).strip():
                entry.language = str(language).strip()
            if thumbnail and str(thumbnail).strip():
                entry.thumbnail = str(thumbnail).strip()
            if status_code:
                entry.status_code = status_code

            # Check if link is acceptable using entry rules; if blocked, remove it
            try:
                from yafr.services.entry_builder import EntryBuilder

                builder = EntryBuilder(session=session)
                acceptable, reason = builder.is_link_acceptable(
                    entry.link, check_duplicates=False
                )
                if not acceptable:
                    logger.info(
                        "Removing entry #%s (%s) because it is no longer acceptable: %s",
                        entry.id,
                        entry.link,
                        reason,
                    )
                    session.delete(entry)
                    session.commit()
                    return {
                        "success": True,
                        "status": "removed",
                        "message": f"Entry #{entry.id} removed: {reason}",
                    }
            except Exception as rule_err:
                logger.debug("Entry rule evaluation skipped or failed: %s", rule_err)

            # Enqueue JOB_LINK_DOWNLOAD_SOCIAL
            try:
                from yafr.db.job_repository import JobRepository

                job_repo = JobRepository(session=session)
                job_repo.enqueue_job(
                    job=JOB_LINK_DOWNLOAD_SOCIAL,
                    subject=str(entry.id),
                    priority=1,
                    enabled=True,
                )
            except Exception as job_err:
                logger.debug("Failed to enqueue %s job: %s", JOB_LINK_DOWNLOAD_SOCIAL, job_err)

            entry.date_update_last = datetime.now(timezone.utc)
            session.commit()

            return {
                "success": True,
                "status": "completed",
                "message": f"Updated entry #{entry.id} metadata (title='{entry.title}').",
                "entry_id": entry.id,
                "title": entry.title,
                "description": entry.description,
            }

        except Exception as err:
            logger.warning(
                "Error updating data for entry #%s (%s): %s",
                getattr(entry, "id", "?"),
                getattr(entry, "link", "?"),
                err,
            )
            try:
                if entry:
                    entry.date_update_last = datetime.now(timezone.utc)
                    session.commit()
            except Exception:
                pass
            return {
                "success": False,
                "status": "error",
                "error": f"Error updating link data: {err}",
            }


class LinkDownloadSocialJobHandler(BaseJobHandler):
    """
    Handler for JOB_LINK_DOWNLOAD_SOCIAL ('link-download-social').

    Downloads social metadata via WebToolsWrapper.get_social_properties() and updates
    rating / visit counters on the entry.
    """

    job_types = (JOB_LINK_DOWNLOAD_SOCIAL, "JOB_LINK_DOWNLOAD_SOCIAL")

    def execute(self, job: BackgroundJob, session: Session) -> Dict[str, Any]:
        """
        Executes social metadata download for the target entry.

        :param job: BackgroundJob record
        :param session: Active database session
        :return: Execution result dictionary
        """
        subject = (job.subject or "").strip()
        entry_repo = EntryRepository(session)
        entry: Optional[LinkDataModel] = None

        if subject.isdigit():
            entry = entry_repo.get_by_id(int(subject))
        elif subject:
            entry = entry_repo.get_by_link(subject)

        if not entry or not entry.link:
            return {
                "success": False,
                "status": "error",
                "error": f"Entry not found or has no URL for subject: '{subject}'",
            }

        try:
            web_client = WebToolsWrapper(url=entry.link, session=session, timeout_s=15)
            social_data = (
                web_client.get_social_properties()
                if hasattr(web_client, "get_social_properties")
                else {}
            ) or {}

            if social_data:
                if social_data.get("rating") is not None:
                    try:
                        entry.page_rating = float(social_data["rating"])
                    except (ValueError, TypeError):
                        pass
                if social_data.get("thumbs_up") is not None:
                    try:
                        entry.page_rating_votes = int(social_data["thumbs_up"])
                    except (ValueError, TypeError):
                        pass
                if social_data.get("view_count") is not None:
                    try:
                        entry.page_rating_visits = int(social_data["view_count"])
                    except (ValueError, TypeError):
                        pass
                session.commit()

            return {
                "success": True,
                "status": "completed",
                "message": f"Updated social metadata for entry #{entry.id}.",
                "entry_id": entry.id,
            }
        except Exception as err:
            logger.warning(
                "Error downloading social data for entry #%s (%s): %s",
                entry.id,
                entry.link,
                err,
            )
            return {
                "success": False,
                "status": "error",
                "error": str(err),
            }

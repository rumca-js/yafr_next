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


class LinkUpdateDataJobHandler(BaseJobHandler):
    """
    Handler for JOB_LINK_UPDATE_DATA ('link-update-data').

    Refreshes link metadata by obtaining a webtoolkit URL handler (BaseUrl or RemoteUrl)
    via WebToolsWrapper, extracting get_title() and get_description(), and updating
    the LinkDataModel entry in SQLite.
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
            # Obtain Url handler like in webtools_service.py (either BaseUrl or RemoteUrl)
            web_client = WebToolsWrapper(url=entry.link, session=session, timeout_s=15)
            url_handler = web_client.url_handler

            response = web_client.get_response()
            if response is None:
                return {
                    "success": False,
                    "status": "error",
                    "error": f"Failed to fetch content from {entry.link}",
                }

            # Fetch BaseUrl.get_title(), BaseUrl.get_description() (or RemoteUrl equivalents)
            title = None
            description = None

            if url_handler is not None:
                if hasattr(url_handler, "get_title"):
                    try:
                        title = url_handler.get_title()
                    except Exception as exc:
                        logger.debug("url_handler.get_title() failed: %s", exc)

                if hasattr(url_handler, "get_description"):
                    try:
                        description = url_handler.get_description()
                    except Exception as exc:
                        logger.debug("url_handler.get_description() failed: %s", exc)

            # Fallback to web_client methods if handler returned None
            if not title and hasattr(web_client, "get_title"):
                title = web_client.get_title()
            if not description and hasattr(web_client, "get_description"):
                description = web_client.get_description()

            # Update entry properties
            if title and title.strip():
                entry.title = title.strip()
            if description and description.strip():
                entry.description = description.strip()

            status_code = web_client.get_status_code()
            if status_code:
                entry.status_code = status_code

            # Additional metadata if present
            if hasattr(url_handler, "get_author"):
                try:
                    author = url_handler.get_author()
                    if author and not entry.author:
                        entry.author = str(author).strip()
                except Exception:
                    pass

            if hasattr(url_handler, "get_language"):
                try:
                    lang = url_handler.get_language()
                    if lang and not entry.language:
                        entry.language = str(lang).strip()
                except Exception:
                    pass

            if hasattr(url_handler, "get_thumbnail"):
                try:
                    thumb = url_handler.get_thumbnail()
                    if thumb and not entry.thumbnail:
                        entry.thumbnail = str(thumb).strip()
                except Exception:
                    pass

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
                "Error updating data for entry #%s (%s): %s", entry.id, entry.link, err
            )
            return {
                "success": False,
                "status": "error",
                "error": f"Error updating link data: {err}",
            }

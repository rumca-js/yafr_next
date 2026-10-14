"""
Job Executor and Task Dispatcher for YAFR.

Processes background tasks sequentially, one at a time, pulling enabled jobs from
the backgroundjob SQLite table in priority/FIFO order, updating retry counts,
archiving completed tasks to backgroundjobhistory, and falling back to source
refreshing when the queue is empty.
"""

from datetime import datetime, timezone
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import (
    BackgroundJob,
    LinkDataModel,
    SearchHistory,
    SourcesTable,
)
from yafr.db.config_repository import ConfigRepository
from yafr.db.entry_repository import EntryRepository
from yafr.db.history_repository import HistoryRepository
from yafr.db.job_repository import JobRepository
from yafr.db.logging_repository import LoggingRepository
from yafr.db.session import close_session, get_session
from yafr.db.source_repository import SourceRepository
from yafr.services.source_service import SourceService

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    Dispatcher and sequential execution runner for background tasks.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        max_retries: int = 3,
        auto_refresh_sources: bool = True,
    ) -> None:
        """
        Initializes the JobExecutor.

        :param session: Optional active database session
        :param max_retries: Maximum failures allowed before a job is disabled
        :param auto_refresh_sources: Whether to check and refresh outdated sources when queue is empty
        """
        self._session = session
        self.max_retries = max_retries
        self.auto_refresh_sources = auto_refresh_sources

    def _get_session(self, session: Optional[Session] = None) -> Session:
        return session or self._session or get_session()

    def process_one(
        self, session: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches and processes exactly one pending background job.

        If no pending jobs are in the queue and auto_refresh_sources is enabled,
        refreshes the oldest outdated source.

        :param session: Optional active database session
        :return: Dict describing task execution results, or None if no work was available
        """
        sess = self._get_session(session)
        job_repo = JobRepository(sess)
        log_repo = LoggingRepository(sess)

        # 1. Fetch next highest-priority enabled job
        job = job_repo.get_next_pending_job()

        if job is None:
            # Check for outdated sources if job queue is empty
            if self.auto_refresh_sources:
                return self._process_outdated_source(sess)
            return None

        job_id = job.id
        job_type = job.job or "unknown"
        job_subject = job.subject or ""
        logger.info(
            "Processing job #%d [%s] subject='%s' (priority=%d, errors=%d)",
            job_id,
            job_type,
            job_subject,
            job.priority,
            job.errors or 0,
        )

        try:
            # 2. Dispatch to matching handler based on job type
            if job_type in ("process-source", "JOB_PROCESS_SOURCE"):
                result = self._handle_process_source(job, sess)
            elif job_type in ("link-update-data", "JOB_LINK_UPDATE_DATA"):
                result = self._handle_link_update_data(job, sess)
            elif job_type in ("cleanup", "JOB_CLEANUP"):
                result = self._handle_cleanup(job, sess)
            else:
                result = self._handle_unknown_job(job, sess)

            success = result.get("success", False)

            if success:
                # 3. On success: archive to history and remove from queue
                job_repo.complete_job(job_id)
                try:
                    log_repo.log(
                        info_text=f"Job #{job_id} [{job_type}] completed successfully.",
                        detail_text=f"Subject: {job_subject} | Result: {result.get('message', 'OK')}",
                        level=20,  # INFO
                    )
                except Exception:
                    pass
                logger.info(
                    "Job #%d [%s] completed and archived to history.", job_id, job_type
                )
            else:
                # 4. On task failure: record error and increment retry count
                err_msg = result.get("error", "Unknown job error")
                updated_job = job_repo.record_job_error(
                    job_id, max_retries=self.max_retries
                )
                try:
                    log_repo.log(
                        info_text=f"Job #{job_id} [{job_type}] failed: {err_msg}",
                        detail_text=f"Subject: {job_subject} | Retries: {updated_job.errors if updated_job else '?'}",
                        level=40,  # ERROR
                    )
                except Exception:
                    pass
                logger.warning("Job #%d recorded failure: %s", job_id, err_msg)

            return {
                "processed": True,
                "job_id": job_id,
                "job_type": job_type,
                "subject": job_subject,
                "success": success,
                "status": result.get("status", "completed" if success else "failed"),
                "message": result.get("message") or result.get("error", ""),
            }

        except Exception as exc:
            # 5. On unhandled exception: record error
            logger.exception(
                "Exception executing job #%d [%s]: %s", job_id, job_type, exc
            )
            job_repo.record_job_error(job_id, max_retries=self.max_retries)
            try:
                log_repo.log(
                    info_text=f"Job #{job_id} [{job_type}] crashed with exception: {exc}",
                    detail_text=str(exc),
                    level=50,  # CRITICAL
                )
            except Exception:
                pass

            return {
                "processed": True,
                "job_id": job_id,
                "job_type": job_type,
                "subject": job_subject,
                "success": False,
                "status": "crashed",
                "message": str(exc),
            }

    def _handle_process_source(
        self, job: BackgroundJob, session: Session
    ) -> Dict[str, Any]:
        """
        Executes a process-source task (fetching and parsing an RSS/Email feed).
        """
        subject = (job.subject or "").strip()
        source_repo = SourceRepository(session)
        source: Optional[SourcesTable] = None

        if subject.isdigit():
            source = source_repo.get_by_id(int(subject))
        elif subject:
            source = source_repo.get_by_url(subject)

        if not source:
            return {
                "success": False,
                "status": "error",
                "error": f"Source not found for subject: '{subject}'",
            }

        if not source.enabled:
            logger.info(
                "Source #%d (%s) is disabled. Skipping fetch.", source.id, source.title
            )
            return {
                "success": True,
                "status": "skipped",
                "message": f"Source #{source.id} is disabled, skipped.",
            }

        return SourceService.fetch_source(source.id, session=session)

    def _handle_link_update_data(
        self, job: BackgroundJob, session: Session
    ) -> Dict[str, Any]:
        """
        Executes a link-update-data task (refreshing entry metadata and timestamps).
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

        entry.date_update_last = datetime.now(timezone.utc)
        session.commit()

        return {
            "success": True,
            "status": "completed",
            "message": f"Updated entry #{entry.id} metadata timestamp.",
        }

    def _handle_cleanup(self, job: BackgroundJob, session: Session) -> Dict[str, Any]:
        """
        Executes a cleanup task (enforcing storage retention quotas).
        """
        config_repo = ConfigRepository(session)
        history_repo = HistoryRepository(session)
        config = config_repo.get_config()

        max_searches = config.max_number_of_user_search or 300
        history_repo.apply_storage_limit(SearchHistory, SearchHistory.id, max_searches)

        return {
            "success": True,
            "status": "completed",
            "message": f"Enforced storage caps: max_searches={max_searches}.",
        }

    def _handle_unknown_job(
        self, job: BackgroundJob, session: Session
    ) -> Dict[str, Any]:
        """
        Fallback handler for unhandled or custom job types.
        """
        logger.info("Executing custom/generic job type: '%s'", job.job)
        return {
            "success": True,
            "status": "completed",
            "message": f"Processed generic task: {job.job}",
        }

    def _process_outdated_source(self, session: Session) -> Optional[Dict[str, Any]]:
        """
        Checks if any enabled source is outdated (> 1h since last fetch) and refreshes it.
        """
        source_repo = SourceRepository(session)
        outdated_sources = source_repo.get_outdated_sources(max_age_seconds=3600)

        if not outdated_sources:
            return None

        source = outdated_sources[0]
        logger.info(
            "Job queue empty. Auto-refreshing oldest outdated source #%d (%s)...",
            source.id,
            source.title or source.url,
        )

        res = SourceService.fetch_source(source.id, session=session)
        return {
            "processed": True,
            "job_id": None,
            "job_type": "source-auto-refresh",
            "subject": source.url,
            "success": res.get("success", False),
            "status": res.get("status", "completed"),
            "message": res.get("message") or res.get("error", "Source refreshed."),
        }

    def run_loop(
        self,
        interval: float = 5.0,
        max_jobs: Optional[int] = None,
        stop_event: Optional[threading.Event] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> int:
        """
        Continuously processes jobs one at a time.

        :param interval: Sleep interval in seconds when idle
        :param max_jobs: Optional maximum jobs to execute before stopping
        :param stop_event: Threading event to signal graceful termination
        :param callback: Optional callable invoked with task result after each job
        :return: Total number of jobs executed
        """
        executed_count = 0

        while True:
            if stop_event and stop_event.is_set():
                break

            result = self.process_one()

            if result and result.get("processed"):
                executed_count += 1
                if callback:
                    callback(result)

                if max_jobs is not None and executed_count >= max_jobs:
                    break
            else:
                # No pending job or work: wait before next poll
                if stop_event:
                    stop_event.wait(interval)
                else:
                    time.sleep(interval)

        return executed_count

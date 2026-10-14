"""
Job Repository Implementation for YAFR.

Manages persistent task queue operations in the backgroundjob and
backgroundjobhistory SQLite tables without external message brokers.
"""

from datetime import datetime, timezone
import logging
from typing import Any, List, Optional
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import BackgroundJob, BackgroundJobHistory
from yafr.db.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository[BackgroundJob]):
    """
    Data access repository for SQLite-backed background task jobs.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        super().__init__(session=session)

    def enqueue_job(
        self,
        job: str,
        subject: str,
        task: Optional[str] = None,
        args: Optional[str] = None,
        priority: int = 0,
        enabled: bool = True,
    ) -> BackgroundJob:
        """
        Enqueues a new background task in the backgroundjob table.

        :param job: Job type identifier (e.g., 'JOB_PROCESS_SOURCE')
        :param subject: Target resource (e.g. source URL or entry ID)
        :param task: Optional sub-task description
        :param args: Optional JSON-encoded task arguments
        :param priority: Integer priority (lower number = higher priority)
        :param enabled: Whether the job is ready for execution
        :return: Created BackgroundJob instance
        """
        bg_job = BackgroundJob(
            job=job,
            subject=subject,
            task=task,
            args=args,
            priority=priority,
            enabled=enabled,
            errors=0,
            date_created=datetime.now(timezone.utc),
        )
        self.session.add(bg_job)
        self.session.commit()
        return bg_job

    def get_next_pending_job(self) -> Optional[BackgroundJob]:
        """
        Pulls the next highest-priority enabled job ready for execution.

        Jobs are prioritized by priority ASC, followed by oldest date_created ASC.

        :return: Next pending BackgroundJob or None
        """
        stmt = (
            select(BackgroundJob)
            .where(BackgroundJob.enabled == True)
            .order_by(BackgroundJob.priority.asc(), BackgroundJob.date_created.asc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def set_job_status(self, job_id: int, enabled: bool) -> bool:
        """
        Pauses or resumes a background job.

        :param job_id: Job ID
        :param enabled: New enabled state
        :return: True if updated, False if not found
        """
        job = self.get_by_id(BackgroundJob, job_id)
        if not job:
            return False
        job.enabled = enabled
        self.session.commit()
        return True

    def record_job_error(
        self, job_id: int, max_retries: int = 3
    ) -> Optional[BackgroundJob]:
        """
        Increments the failure counter for a job. If consecutive errors
        reach max_retries, disables the job to avoid blocking the queue.

        :param job_id: Job ID
        :param max_retries: Max allowed failures before disabling (default: 3)
        :return: Updated BackgroundJob or None
        """
        job = self.get_by_id(BackgroundJob, job_id)
        if not job:
            return None

        job.errors = (job.errors or 0) + 1
        if job.errors >= max_retries:
            job.enabled = False
            logger.warning(
                "Job id=%d (%s) disabled after reaching %d failures",
                job.id,
                job.job,
                job.errors,
            )

        self.session.commit()
        return job

    def complete_job(self, job_id: int) -> bool:
        """
        Archives a completed task into backgroundjobhistory and deletes it from backgroundjob.

        :param job_id: Job ID
        :return: True if completed and archived, False if not found
        """
        job = self.get_by_id(BackgroundJob, job_id)
        if not job:
            return False

        # Archive to history
        history_entry = BackgroundJobHistory(
            job=job.job,
            subject=job.subject,
            task=job.task,
            args=job.args,
            date_created=job.date_created,
        )
        self.session.add(history_entry)

        # Delete active task
        self.session.delete(job)
        self.session.commit()
        return True

    def list_jobs(
        self,
        enabled: Optional[bool] = None,
        order_by: str = "priority",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[BackgroundJob]:
        """
        Lists background jobs with optional status filter and sorting.

        :param enabled: Optional filter by enabled state
        :param order_by: Sorting column ('priority', 'date_created', 'errors')
        :param limit: Maximum rows to return
        :param offset: Number of rows to skip
        :return: List of BackgroundJob instances
        """
        stmt = select(BackgroundJob)
        if enabled is not None:
            stmt = stmt.where(BackgroundJob.enabled == enabled)

        if order_by == "date_created":
            stmt = stmt.order_by(BackgroundJob.date_created.desc())
        elif order_by == "errors":
            stmt = stmt.order_by(BackgroundJob.errors.desc())
        else:
            stmt = stmt.order_by(
                BackgroundJob.priority.asc(), BackgroundJob.date_created.asc()
            )

        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.session.execute(stmt).scalars().all())

    def delete_job(self, job_id: int) -> bool:
        """
        Deletes a job from the queue.

        :param job_id: Job ID
        :return: True if deleted, False if not found
        """
        job = self.get_by_id(BackgroundJob, job_id)
        if not job:
            return False
        self.session.delete(job)
        self.session.commit()
        return True

    def count_error_jobs(self) -> int:
        """
        Counts jobs that have logged errors.

        :return: Total number of jobs with errors > 0
        """
        stmt = select(func.count(BackgroundJob.id)).where(BackgroundJob.errors > 0)
        return self.session.execute(stmt).scalar() or 0

    def clear_history(self) -> int:
        """
        Clears all records in the backgroundjobhistory table.

        :return: Number of deleted rows
        """
        stmt = delete(BackgroundJobHistory)
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount or 0

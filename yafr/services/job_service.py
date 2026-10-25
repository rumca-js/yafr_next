"""
Job Service Implementation for YAFR.

Coordinates background task queue operations, job creation, state transitions
(pause, resume), batch mutations, and prioritization according to project specifications.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import BackgroundJob
from yafr.db.job_repository import JobRepository
from yafr.db.session import get_session

logger = logging.getLogger(__name__)

# Standard Background Job Types
JOB_LINK_UPDATE_DATA = "link-update-data"
JOB_PROCESS_SOURCE = "process-source"
JOB_CLEANUP = "cleanup"


class JobService:
    """
    Domain service managing background task jobs and queue workflows.
    """

    @classmethod
    def list_jobs(
        cls,
        enabled: Optional[bool] = None,
        order_by: str = "priority",
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        has_errors: Optional[bool] = None,
        job_type: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> List[BackgroundJob]:
        """
        Retrieves a paginated list of background jobs matching the criteria.

        :param enabled: Filter by active (True) or paused (False) state
        :param order_by: Sorting field ('priority', 'date_created', 'errors', 'enabled')
        :param limit: Maximum jobs to return
        :param offset: Number of records to skip
        :param has_errors: Filter by error presence
        :param job_type: Filter by specific job identifier
        :param session: Optional active database session
        :return: List of BackgroundJob instances
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.list_jobs(
            enabled=enabled,
            order_by=order_by,
            limit=limit,
            offset=offset,
            has_errors=has_errors,
            job_type=job_type,
        )

    @classmethod
    def count_jobs(
        cls,
        enabled: Optional[bool] = None,
        has_errors: Optional[bool] = None,
        job_type: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> int:
        """
        Counts total background jobs matching the given filters.

        :param enabled: Filter by active (True) or paused (False) state
        :param has_errors: Filter by error presence
        :param job_type: Filter by specific job identifier
        :param session: Optional active database session
        :return: Total matching count
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.count_jobs(
            enabled=enabled,
            has_errors=has_errors,
            job_type=job_type,
        )

    @classmethod
    def get_job(
        cls, job_id: int, session: Optional[Session] = None
    ) -> Optional[BackgroundJob]:
        """
        Retrieves a single background job by primary key.

        :param job_id: Primary key ID
        :param session: Optional active database session
        :return: BackgroundJob instance or None
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.get_by_id(BackgroundJob, job_id)

    @classmethod
    def create_job(
        cls,
        job: str,
        subject: str,
        task: Optional[str] = None,
        args: Optional[str] = None,
        priority: int = 1,
        enabled: bool = True,
        session: Optional[Session] = None,
    ) -> BackgroundJob:
        """
        Enqueues a new background task.

        :param job: Job type identifier (e.g. 'link-update-data', 'process-source')
        :param subject: Target URL, source ID, or resource string
        :param task: Optional sub-task description
        :param args: Optional arguments (e.g. JSON string)
        :param priority: Integer priority (lower = higher priority)
        :param enabled: Ready status (default: True)
        :param session: Optional active database session
        :return: Newly created BackgroundJob instance
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.enqueue_job(
            job=job,
            subject=subject,
            task=task,
            args=args,
            priority=priority,
            enabled=enabled,
        )

    @classmethod
    def pause_job(cls, job_id: int, session: Optional[Session] = None) -> bool:
        """
        Pauses an active job by setting enabled = False.

        :param job_id: Job ID
        :param session: Optional active database session
        :return: True if updated, False if not found
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.set_job_status(job_id, enabled=False)

    @classmethod
    def resume_job(cls, job_id: int, session: Optional[Session] = None) -> bool:
        """
        Resumes a paused job by setting enabled = True.

        :param job_id: Job ID
        :param session: Optional active database session
        :return: True if updated, False if not found
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.set_job_status(job_id, enabled=True)

    @classmethod
    def delete_job(cls, job_id: int, session: Optional[Session] = None) -> bool:
        """
        Deletes a background task by ID.

        :param job_id: Job ID
        :param session: Optional active database session
        :return: True if deleted, False if not found
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.delete_job(job_id)

    @classmethod
    def batch_action(
        cls,
        job_ids: List[int],
        action: str,
        session: Optional[Session] = None,
    ) -> int:
        """
        Executes a batch mutation across multiple background jobs.

        :param job_ids: List of job IDs
        :param action: Action name: 'pause', 'resume', or 'delete'
        :param session: Optional active database session
        :return: Number of affected jobs
        """
        if not job_ids:
            return 0

        sess = session or get_session()
        repo = JobRepository(sess)

        if action == "pause":
            return repo.batch_set_status(job_ids, enabled=False)
        elif action == "resume":
            return repo.batch_set_status(job_ids, enabled=True)
        elif action == "delete":
            return repo.delete_jobs(job_ids)
        else:
            raise ValueError(f"Unsupported batch action: {action}")

    @classmethod
    def get_job_types(cls, session: Optional[Session] = None) -> List[str]:
        """
        Retrieves all distinct job type names currently in the database.

        :param session: Optional active database session
        :return: List of job type strings
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.get_distinct_job_types()

    @classmethod
    def count_error_jobs(cls, session: Optional[Session] = None) -> int:
        """
        Retrieves total number of jobs with errors > 0.

        :param session: Optional active database session
        :return: Error job count
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.count_error_jobs()

    @classmethod
    def clear_all_jobs(cls, session: Optional[Session] = None) -> int:
        """
        Deletes all jobs from the queue.

        :param session: Optional active database session
        :return: Number of deleted jobs
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.clear_all_jobs()

    @classmethod
    def clear_error_jobs(cls, session: Optional[Session] = None) -> int:
        """
        Deletes all jobs with errors > 0 from the queue.

        :param session: Optional active database session
        :return: Number of deleted jobs
        """
        sess = session or get_session()
        repo = JobRepository(sess)
        return repo.clear_error_jobs()

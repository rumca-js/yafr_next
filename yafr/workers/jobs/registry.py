"""
Job Registry for YAFR Background Jobs.

Maps job types to their corresponding modular handlers, enabling easy extension
as new background job types are added.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import BackgroundJob
from yafr.workers.jobs.base import BaseJobHandler
from yafr.workers.jobs.link_jobs import (
    LinkDownloadSocialJobHandler,
    LinkUpdateDataJobHandler,
)
from yafr.workers.jobs.source_jobs import ProcessSourceJobHandler
from yafr.workers.jobs.system_jobs import CleanupJobHandler, GenericJobHandler


class JobRegistry:
    """
    Central dispatcher registry mapping BackgroundJob types to modular handlers.
    """

    def __init__(self) -> None:
        self._handlers: List[BaseJobHandler] = []
        self._fallback_handler: BaseJobHandler = GenericJobHandler()

    def register(self, handler: BaseJobHandler) -> None:
        """
        Registers a job handler.
        """
        self._handlers.append(handler)

    def get_handler(self, job_type: str) -> BaseJobHandler:
        """
        Retrieves the registered handler matching the job type, or the generic fallback.
        """
        for handler in self._handlers:
            if handler.can_handle(job_type):
                return handler
        return self._fallback_handler

    def dispatch(self, job: BackgroundJob, session: Session) -> Dict[str, Any]:
        """
        Routes the job to its registered handler and returns the execution result.
        """
        job_type = job.job or "unknown"
        handler = self.get_handler(job_type)
        return handler.execute(job, session)


def create_default_registry() -> JobRegistry:
    """
    Constructs and populates the default JobRegistry with standard system handlers.
    """
    registry = JobRegistry()
    registry.register(ProcessSourceJobHandler())
    registry.register(LinkUpdateDataJobHandler())
    registry.register(LinkDownloadSocialJobHandler())
    registry.register(CleanupJobHandler())
    return registry


# Singleton default registry instance
default_registry = create_default_registry()

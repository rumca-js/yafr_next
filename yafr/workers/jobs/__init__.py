"""
Modular Background Jobs Package for YAFR.

Separates discrete job logic (sources, links, cleanup, system) from the
sequential dispatcher / executor loop.
"""

from yafr.workers.jobs.base import BaseJobHandler
from yafr.workers.jobs.link_jobs import JOB_LINK_UPDATE_DATA, LinkUpdateDataJobHandler
from yafr.workers.jobs.registry import (
    JobRegistry,
    create_default_registry,
    default_registry,
)
from yafr.workers.jobs.source_jobs import JOB_PROCESS_SOURCE, ProcessSourceJobHandler
from yafr.workers.jobs.system_jobs import (
    JOB_CLEANUP,
    CleanupJobHandler,
    GenericJobHandler,
)

__all__ = [
    "BaseJobHandler",
    "JobRegistry",
    "create_default_registry",
    "default_registry",
    "LinkUpdateDataJobHandler",
    "ProcessSourceJobHandler",
    "CleanupJobHandler",
    "GenericJobHandler",
    "JOB_LINK_UPDATE_DATA",
    "JOB_PROCESS_SOURCE",
    "JOB_CLEANUP",
]

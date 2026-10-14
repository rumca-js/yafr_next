"""
Logging Repository Implementation for YAFR.

Persists structured application events into the applogging SQLite table
with standard severity levels and FIFO retention management.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import AppLogging
from yafr.db.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class LoggingRepository(BaseRepository[AppLogging]):
    """
    Data access repository for application logging events.
    """

    # Severity Level Constants matching standard Python logging
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def __init__(self, session: Optional[Session] = None) -> None:
        super().__init__(session=session)

    def log(
        self,
        info_text: str,
        detail_text: Optional[str] = None,
        level: int = INFO,
        max_limit: int = 2000,
    ) -> AppLogging:
        """
        Records an event log entry and enforces rolling FIFO retention.

        :param info_text: Brief description of the event
        :param detail_text: Optional detailed message, traceback, or context
        :param level: Integer severity level (10=DEBUG, 20=INFO, 30=WARN, 40=ERROR, 50=CRIT)
        :param max_limit: Maximum log rows to retain in database (default: 2000)
        :return: Persisted AppLogging instance
        """
        entry = AppLogging(
            info_text=info_text[:2000] if info_text else "",
            detail_text=detail_text[:2000] if detail_text else None,
            level=level,
            date=datetime.now(timezone.utc),
        )
        self.session.add(entry)
        self.session.commit()

        # Enforce storage cap
        self.apply_storage_limit(AppLogging, AppLogging.id, max_limit)
        return entry

    def list_logs(
        self,
        min_level: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AppLogging]:
        """
        Retrieves log events ordered by most recent first.

        :param min_level: Optional minimum severity level filter
        :param limit: Maximum rows to return (default: 100)
        :param offset: Number of rows to skip
        :return: List of AppLogging instances
        """
        stmt = select(AppLogging).order_by(AppLogging.id.desc())
        if min_level is not None:
            stmt = stmt.where(AppLogging.level >= min_level)

        if offset > 0:
            stmt = stmt.offset(offset)
        if limit > 0:
            stmt = stmt.limit(limit)

        return list(self.session.execute(stmt).scalars().all())

    def count_logs(self, min_level: Optional[int] = None) -> int:
        """
        Counts log entries matching optional severity filter.

        :param min_level: Optional minimum severity level filter
        :return: Total count of matching log entries
        """
        stmt = select(func.count(AppLogging.id))
        if min_level is not None:
            stmt = stmt.where(AppLogging.level >= min_level)
        return self.session.execute(stmt).scalar() or 0

    def delete_log(self, log_id: int) -> bool:
        """
        Deletes a single log entry by ID.

        :param log_id: Primary key of the log entry
        :return: True if deleted, False if not found
        """
        entry = self.get_by_id(AppLogging, log_id)
        if not entry:
            return False
        self.session.delete(entry)
        self.session.commit()
        return True

    def clear_logs(self) -> int:
        """
        Truncates all entries in the applogging table.

        :return: Count of deleted rows
        """
        stmt = delete(AppLogging)
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount or 0

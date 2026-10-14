"""
Base Repository Implementation for YAFR.

Provides generic CRUD helper methods, transaction management,
and FIFO storage quota enforcement across all data access repositories.
"""

import logging
from typing import Any, Generic, Iterable, List, Optional, Type, TypeVar
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from yafr.db.session import get_session

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Abstract base repository for database operations.

    Encapsulates SQLAlchemy session lifecycle, generic persistence routines,
    and automatic FIFO storage limit management for history tables.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        """
        Initializes the repository with an optional session.

        :param session: Optional explicit SQLAlchemy Session instance.
                        If omitted, the thread-local scoped session is used.
        """
        self._session = session

    @property
    def session(self) -> Session:
        """
        Retrieves the active session for the current thread or unit of work.

        :return: Active SQLAlchemy Session
        """
        if self._session is not None:
            return self._session
        return get_session()

    def commit(self) -> None:
        """
        Commits all pending changes to the SQLite database.
        """
        try:
            self.session.commit()
        except Exception as err:
            self.session.rollback()
            logger.error("Database commit failed, rolled back: %s", err)
            raise

    def rollback(self) -> None:
        """
        Rolls back uncommitted changes in the current session.
        """
        self.session.rollback()

    def get_by_id(self, model_cls: Type[T], entity_id: int) -> Optional[T]:
        """
        Retrieves an entity by its primary key identifier.

        :param model_cls: Mapped model class
        :param entity_id: Primary key ID
        :return: Matching entity instance or None
        """
        return self.session.get(model_cls, entity_id)

    def add(self, entity: T) -> T:
        """
        Adds a new entity to the persistence context and flushes.

        :param entity: Model entity instance
        :return: Persisted entity with assigned ID
        """
        self.session.add(entity)
        self.session.flush()
        return entity

    def add_all(self, entities: Iterable[T]) -> None:
        """
        Adds multiple entities to the persistence context.

        :param entities: Collection of model entity instances
        """
        self.session.add_all(entities)
        self.session.flush()

    def update(self, entity: T) -> T:
        """
        Merges and flushes updates to an entity.

        :param entity: Model entity instance
        :return: Updated entity instance
        """
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def delete(self, entity: T) -> None:
        """
        Deletes an entity from the database.

        :param entity: Model entity instance to delete
        """
        self.session.delete(entity)
        self.session.flush()

    def list_all(
        self,
        model_cls: Type[T],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[Any] = None,
    ) -> List[T]:
        """
        Lists entities of a given model with optional pagination and ordering.

        :param model_cls: Mapped model class
        :param limit: Maximum number of rows to return
        :param offset: Number of rows to skip
        :param order_by: SQLAlchemy column or ordering clause
        :return: List of entity instances
        """
        stmt = select(model_cls)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count(self, model_cls: Type[T], *clauses: Any) -> int:
        """
        Counts rows in a table matching optional criteria.

        :param model_cls: Mapped model class
        :param clauses: SQLAlchemy filter conditions
        :return: Total number of matching rows
        """
        stmt = select(func.count()).select_from(model_cls)
        if clauses:
            stmt = stmt.where(*clauses)
        result = self.session.execute(stmt).scalar()
        return result or 0

    def apply_storage_limit(
        self, model_cls: Type[T], order_col: Any, max_limit: int
    ) -> int:
        """
        Enforces FIFO storage retention on history and log tables.

        When row count exceeds max_limit, deletes the oldest entries
        ordered by order_col ASC.

        :param model_cls: Mapped model class with an 'id' primary key
        :param order_col: Column indicating age/sequence (e.g., date, id)
        :param max_limit: Maximum allowed row count
        :return: Number of evicted rows
        """
        if max_limit <= 0:
            return 0

        total = self.count(model_cls)
        if total <= max_limit:
            return 0

        excess = total - max_limit
        # Retrieve IDs of the oldest excess rows
        id_col = getattr(model_cls, "id")
        old_ids_stmt = select(id_col).order_by(order_col.asc()).limit(excess)
        ids_to_delete = list(self.session.execute(old_ids_stmt).scalars().all())

        if not ids_to_delete:
            return 0

        delete_stmt = delete(model_cls).where(id_col.in_(ids_to_delete))
        self.session.execute(delete_stmt)
        self.commit()

        logger.info(
            "Evicted %d oldest records from %s to maintain limit of %d",
            len(ids_to_delete),
            getattr(model_cls, "__tablename__", str(model_cls)),
            max_limit,
        )
        return len(ids_to_delete)

"""
SQLite Database Session and Engine Factory for YAFR.

This module initializes the SQLAlchemy engine with WAL journal mode,
provides thread-safe scoped sessions, and manages schema reconciliation.
"""

from contextlib import contextmanager
import logging
import os
from pathlib import Path
import sqlite3
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session
import linkarchivetools.model.definitions as definitions

logger = logging.getLogger(__name__)

# Global singletons for engine and session factory
_engine: Optional[Engine] = None
_Session: Optional[scoped_session] = None


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    """
    Configures SQLite connection pragmas for performance and concurrency.

    - PRAGMA journal_mode=WAL: Enables Write-Ahead Logging for concurrent readers/writers.
    - PRAGMA foreign_keys=ON: Enforces relational integrity across tables.
    - PRAGMA synchronous=NORMAL: Balances durability and write speed in WAL mode.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.Error as err:
            logger.warning("Failed to apply SQLite PRAGMAs: %s", err)
        finally:
            cursor.close()


def _reconcile_schema(engine: Engine) -> None:
    """
    Reconciles SQLite database schema with linkarchivetools models.

    Creates any missing tables and safely executes ALTER TABLE ADD COLUMN
    for any model columns missing in pre-existing database tables.

    :param engine: Active SQLAlchemy Engine
    """
    # Create missing tables if they do not exist
    definitions.create_tables(engine)

    # Check for missing columns in existing tables
    with engine.connect() as conn:
        dialect = engine.dialect
        for table_name, table in definitions.Base.metadata.tables.items():
            result = conn.execute(text(f"PRAGMA table_info({table_name});"))
            existing_cols = {row[1] for row in result.fetchall()}
            if not existing_cols:
                continue

            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(dialect)
                    alter_query = (
                        f'ALTER TABLE {table_name} ADD COLUMN "{col.name}" {col_type};'
                    )
                    try:
                        conn.execute(text(alter_query))
                        conn.commit()
                        logger.info(
                            "Added missing column '%s' to table '%s'",
                            col.name,
                            table_name,
                        )
                    except Exception as err:
                        logger.warning(
                            "Failed to add column '%s' to '%s': %s",
                            col.name,
                            table_name,
                            err,
                        )


def init_db(db_path: Optional[str] = None, sync_schema: bool = True) -> Engine:
    """
    Initializes the database engine and scoped session maker.

    :param db_path: Filepath or URL for SQLite database (e.g., 'data/table.db' or ':memory:')
    :param sync_schema: Whether to run table creation and schema reconciliation
    :return: Initialized SQLAlchemy Engine
    """
    global _engine, _Session

    if db_path is None:
        db_path = os.environ.get("YAFR_DATABASE_PATH", "data/table.db")

    if db_path == ":memory:":
        db_url = "sqlite:///:memory:"
    elif db_path.startswith("sqlite:///"):
        db_url = db_path
    else:
        # Ensure parent directory exists for file-based database
        db_file = Path(db_path).resolve()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{db_file}"

    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
    }
    if db_path == ":memory:":
        from sqlalchemy.pool import StaticPool

        engine_kwargs["poolclass"] = StaticPool

    _engine = create_engine(
        db_url,
        **engine_kwargs,
    )

    session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    _Session = scoped_session(session_factory)

    if sync_schema:
        _reconcile_schema(_engine)

    logger.info("YAFR Database initialized at: %s", db_url)
    return _engine


def get_engine() -> Engine:
    """
    Retrieves the global SQLAlchemy engine instance.

    :return: Active Engine instance
    :raises RuntimeError: If init_db() has not been called
    """
    global _engine
    if _engine is None:
        _engine = init_db()
    return _engine


def get_session() -> Session:
    """
    Retrieves the thread-local scoped SQLAlchemy Session.

    :return: Scoped Session instance
    :raises RuntimeError: If database has not been initialized
    """
    global _Session
    if _Session is None:
        init_db()
    return _Session()


def close_session() -> None:
    """
    Removes the thread-local scoped session, releasing underlying connections.
    """
    global _Session
    if _Session is not None:
        _Session.remove()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager providing a transactional scope around a series of operations.

    Automatically commits on success or rolls back on exception, then closes the session.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        close_session()

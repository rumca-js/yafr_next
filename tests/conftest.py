"""
Pytest Fixtures for YAFR test suite.

Provides isolated in-memory SQLite database sessions and Flask test client.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import linkarchivetools.model.definitions as definitions
from yafr.app import create_app
from yafr.db import close_session, init_db


@pytest.fixture(scope="function")
def in_memory_db():
    """
    Initializes an isolated in-memory SQLite database for testing.
    """
    engine = init_db(db_path=":memory:", sync_schema=True)
    yield engine
    close_session()


@pytest.fixture(scope="function")
def test_app():
    """
    Creates a Flask test application configured with an in-memory SQLite database.
    """
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": ":memory:",
            "SECRET_KEY": "test-key",
        }
    )
    yield app
    close_session()


@pytest.fixture(scope="function")
def test_client(test_app):
    """
    Yields Flask test client.
    """
    return test_app.test_client()

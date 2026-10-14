"""
Integration tests for YAFR web routes and search views.
"""

import unittest
from yafr.app import create_app
from yafr.db import (
    EntryRepository,
    HistoryRepository,
    close_session,
    get_session,
    init_db,
)


class TestEntryRoutes(unittest.TestCase):
    """
    Test suite for EntriesListView and search routes.
    """

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": ":memory:",
                "SECRET_KEY": "test-key",
            }
        )
        self.client = self.app.test_client()
        self.session = get_session()

        # Seed sample entries
        entry_repo = EntryRepository(self.session)
        self.e1 = entry_repo.add_entry(
            link="https://example.com/py1",
            title="Advanced Python Programming",
            description="Deep dive into Python internals and metaclasses",
        )
        entry_repo.set_tags(self.e1.id, ["python", "advanced"])

        self.e2 = entry_repo.add_entry(
            link="https://example.com/flask",
            title="Flask Web Development",
            description="Building web applications using Python and Flask",
        )
        entry_repo.set_tags(self.e2.id, ["flask", "web"])

    def tearDown(self):
        close_session()

    def test_search_view_empty_query(self):
        """GET / without query renders centered search input."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("main-search-input", html)
        self.assertIn("Search entries", html)

    def test_search_view_with_query(self):
        """GET / with query executes search and returns matching entries."""
        response = self.client.get("/?q=Python")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Advanced Python Programming", html)
        self.assertIn("Found", html)

        # Check search query was recorded in history
        history_repo = HistoryRepository(self.session)
        recent = history_repo.get_recent_searches()
        self.assertIn("Python", recent)

    def test_search_view_with_operator_and_filter(self):
        """GET /?q=title=Flask&filter=date_published works properly."""
        response = self.client.get("/?q=title=Flask&filter=date_published")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Flask Web Development", html)
        self.assertNotIn("Advanced Python Programming", html)

    def test_search_view_tag_search(self):
        """GET /?q=tag:flask matches tagged entry."""
        response = self.client.get("/?q=tag:flask")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Flask Web Development", html)

    def test_404_error_handler(self):
        """Non-existent URL triggers custom 404 handler."""
        response = self.client.get("/non-existent-endpoint")
        self.assertEqual(response.status_code, 404)
        html = response.get_data(as_text=True)
        self.assertIn("Page or entry not found", html)


if __name__ == "__main__":
    unittest.main()

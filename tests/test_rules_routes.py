"""
Unit and integration tests for EntryRules and BlockEntry web routes.
"""

import unittest
from yafr.app import create_app
from yafr.db import (
    BlockEntryRepository,
    RulesRepository,
    close_session,
    get_session,
)


class TestRulesRoutes(unittest.TestCase):
    """
    Test suite for Entry Rules views, block URL modal/routes, and rule management.
    """

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": ":memory:",
                "SECRET_KEY": "test-key-rules-routes",
            }
        )
        self.client = self.app.test_client()
        self.session = get_session()
        self.rules_repo = RulesRepository(self.session)
        self.block_repo = BlockEntryRepository(self.session)

    def tearDown(self):
        close_session()

    def test_rules_list_contains_add_rule_and_block_url_buttons(self):
        """GET /rules renders the page with both 'Add Rule' and 'Block Url' buttons."""
        response = self.client.get("/rules")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Add Rule", html)
        self.assertIn("Block Url", html)
        self.assertIn("blockUrlModal", html)

    def test_post_block_url_creates_block_entry_and_redirects(self):
        """POST /rules/block-url creates a BlockEntry record and redirects to /rules."""
        response = self.client.post(
            "/rules/block-url",
            data={"url": "tracker.adnetwork.com"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("tracker.adnetwork.com", html)
        self.assertIn("added successfully", html.lower())

        # Verify in database
        entry = self.block_repo.get_entry_by_url("tracker.adnetwork.com")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.url, "tracker.adnetwork.com")

    def test_post_block_url_empty_does_not_create(self):
        """POST /rules/block-url with empty URL flashes warning and creates nothing."""
        initial_count = self.block_repo.count_entries()
        response = self.client.post(
            "/rules/block-url",
            data={"url": "   "},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.block_repo.count_entries(), initial_count)

    def test_get_block_url_standalone_page(self):
        """GET /rules/block-url renders standalone Block URL form."""
        response = self.client.get("/rules/block-url")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Block URL / Domain", html)
        self.assertIn("action", html)

    def test_post_delete_block_entry(self):
        """POST /rules/block-entry/<id>/delete removes the BlockEntry."""
        entry = self.block_repo.add_entry("malicious.site")
        self.assertIsNotNone(self.block_repo.get_entry(entry.id))

        response = self.client.post(
            f"/rules/block-entry/{entry.id}/delete",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("removed", html.lower())
        self.assertIsNone(self.block_repo.get_entry(entry.id))

    def test_post_delete_nonexistent_block_entry(self):
        """POST /rules/block-entry/<id>/delete with non-existent ID redirects safely."""
        response = self.client.post(
            "/rules/block-entry/99999/delete",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

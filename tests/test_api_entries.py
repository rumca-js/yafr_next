"""
Unit tests for Entry and History REST / JSON API endpoints.
"""

import unittest
from yafr.app import create_app
from yafr.db import EntryRepository, HistoryRepository, close_session, get_session


class TestApiEntries(unittest.TestCase):
    """
    Test suite for /api/entries/* and /api/history/* JSON endpoints.
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
        self.repo = EntryRepository(self.session)

        self.entry = self.repo.add_entry(
            link="https://example.com/api-test",
            title="API Test Entry",
            description="Testing API endpoints",
        )

    def tearDown(self):
        close_session()

    def test_api_vote_entry(self):
        """POST /api/entries/<id>/vote records rating vote."""
        # Upvote
        res = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={"direction": "up"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["page_rating_votes"], 1)

        # Downvote
        res2 = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={"direction": "down"},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["data"]["page_rating_votes"], 0)

        # Explicit vote
        res3 = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={"vote": 75},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.get_json()["data"]["page_rating_votes"], 75)

    def test_api_toggle_bookmark(self):
        """POST /api/entries/<id>/bookmark toggles bookmark flag."""
        res = self.client.post(f"/api/entries/{self.entry.id}/bookmark")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["data"]["bookmarked"])

        res2 = self.client.post(f"/api/entries/{self.entry.id}/bookmark")
        self.assertEqual(res2.status_code, 200)
        self.assertFalse(res2.get_json()["data"]["bookmarked"])

    def test_api_toggle_read_later(self):
        """POST /api/entries/<id>/read-later toggles Read Later."""
        res = self.client.post(f"/api/entries/{self.entry.id}/read-later")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["data"]["read_later"])

        res2 = self.client.post(f"/api/entries/{self.entry.id}/read-later")
        self.assertEqual(res2.status_code, 200)
        self.assertFalse(res2.get_json()["data"]["read_later"])

    def test_api_record_visit(self):
        """POST /api/entries/<id>/visit increments visit counter."""
        res = self.client.post(f"/api/entries/{self.entry.id}/visit")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["visits"], 1)

    def test_api_set_status(self):
        """POST /api/entries/<id>/status updates manual status code."""
        res = self.client.post(
            f"/api/entries/{self.entry.id}/status",
            json={"status_code": 400},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["manual_status_code"], 400)

    def test_api_update_tags(self):
        """POST /api/entries/<id>/tags updates tags."""
        res = self.client.post(
            f"/api/entries/{self.entry.id}/tags",
            json={"tags": ["python", "flask", "web"]},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["tags"], ["flask", "python", "web"])

    def test_api_delete_entry(self):
        """DELETE /api/entries/<id> deletes entry."""
        res = self.client.delete(f"/api/entries/{self.entry.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(self.repo.get_by_id(self.entry.id))

    def test_api_batch_delete(self):
        """POST /api/entries/batch-delete deletes multiple entries."""
        e2 = self.repo.add_entry(link="https://example.com/e2", title="E2")
        e3 = self.repo.add_entry(link="https://example.com/e3", title="E3")

        res = self.client.post(
            "/api/entries/batch-delete",
            json={"ids": [e2.id, e3.id]},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["deleted_count"], 2)

    def test_api_autocomplete(self):
        """GET /api/history/autocomplete returns query suggestions."""
        history = HistoryRepository(self.session)
        history.add_search("youtube gaming")
        history.add_search("youtube music")
        history.add_search("python tutorial")

        res = self.client.get("/api/history/autocomplete?q=you")
        self.assertEqual(res.status_code, 200)
        suggestions = res.get_json()["data"]["suggestions"]
        self.assertIn("youtube music", suggestions)
        self.assertIn("youtube gaming", suggestions)
        self.assertNotIn("python tutorial", suggestions)


if __name__ == "__main__":
    unittest.main()

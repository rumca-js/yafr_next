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
        """POST /api/entries/<id>/vote sets rating vote to a direct number."""
        # Set vote to 70 directly
        res = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={"vote": 70},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["page_rating_votes"], 70)

        # Set vote to negative number directly (-45)
        res2 = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={"vote": -45},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["data"]["page_rating_votes"], -45)

        # Missing vote parameter returns 400
        res_missing = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={},
        )
        self.assertEqual(res_missing.status_code, 400)

        # Out-of-bounds vote number returns 400
        res_overflow = self.client.post(
            f"/api/entries/{self.entry.id}/vote",
            json={"vote": 150},
        )
        self.assertEqual(res_overflow.status_code, 400)

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

    def test_api_mark_active_and_dead(self):
        """POST /api/entries/<id>/mark-active and /mark-dead sets manual status codes."""
        # Mark dead (400)
        res_dead = self.client.post(f"/api/entries/{self.entry.id}/mark-dead")
        self.assertEqual(res_dead.status_code, 200)
        self.assertEqual(res_dead.get_json()["data"]["manual_status_code"], 400)
        self.assertEqual(self.repo.get_by_id(self.entry.id).manual_status_code, 400)

        # Mark active (200)
        res_active = self.client.post(f"/api/entries/{self.entry.id}/mark-active")
        self.assertEqual(res_active.status_code, 200)
        self.assertEqual(res_active.get_json()["data"]["manual_status_code"], 200)
        self.assertEqual(self.repo.get_by_id(self.entry.id).manual_status_code, 200)

    def test_api_update_data_enqueues_job(self):
        """POST /api/entries/<id>/update-data enqueues background link-update-data job."""
        res = self.client.post(f"/api/entries/{self.entry.id}/update-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["entry_id"], self.entry.id)
        self.assertIn("job_id", data)

    def test_api_reset_data(self):
        """POST /api/entries/<id>/reset-data clears hashes and status code."""
        self.entry.contents_hash = b"fake-hash"
        self.entry.status_code = 200
        self.session.commit()

        res = self.client.post(f"/api/entries/{self.entry.id}/reset-data")
        self.assertEqual(res.status_code, 200)
        refreshed = self.repo.get_by_id(self.entry.id)
        self.assertIsNone(refreshed.contents_hash)
        self.assertEqual(refreshed.status_code, 0)

    def test_api_visit_with_transition(self):
        """POST /api/entries/<id>/visit with from_entry_id records navigation transition."""
        e2 = self.repo.add_entry(link="https://example.com/target-page", title="Target")
        res = self.client.post(
            f"/api/entries/{e2.id}/visit",
            json={"from_entry_id": self.entry.id},
        )
        self.assertEqual(res.status_code, 200)
        history = HistoryRepository(self.session)
        transitions = history.get_transitions_from(self.entry.id)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].entry_to_id, e2.id)


if __name__ == "__main__":
    unittest.main()

"""
Unit and integration tests for background task execution and JobExecutor.
"""

from datetime import datetime, timedelta, timezone
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import select
from linkarchivetools.model.definitions import (
    BackgroundJob,
    BackgroundJobHistory,
    LinkDataModel,
    SearchHistory,
    SourcesTable,
)
from yafr.app import create_app
from yafr.db import (
    EntryRepository,
    HistoryRepository,
    JobRepository,
    SourceRepository,
    close_session,
    get_session,
    init_db,
)
from yafr.workers.job_executor import JobExecutor


class TestJobExecutor(unittest.TestCase):
    """
    Test suite for JobExecutor sequential execution and task dispatching.
    """

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": ":memory:",
                "SECRET_KEY": "test-key-workers",
            }
        )
        self.session = get_session()
        self.job_repo = JobRepository(self.session)
        self.source_repo = SourceRepository(self.session)
        self.entry_repo = EntryRepository(self.session)
        self.history_repo = HistoryRepository(self.session)

    def tearDown(self):
        close_session()

    def test_process_cleanup_job(self):
        """JobExecutor processes cleanup task and archives it to history."""
        # Seed searches exceeding limit
        for i in range(10):
            self.history_repo.add_search(f"query_{i}")

        job = self.job_repo.enqueue_job(
            job="cleanup",
            subject="system",
            priority=1,
            enabled=True,
        )

        executor = JobExecutor(session=self.session, auto_refresh_sources=False)
        result = executor.process_one(session=self.session)

        self.assertIsNotNone(result)
        self.assertTrue(result["processed"])
        self.assertEqual(result["job_id"], job.id)
        self.assertTrue(result["success"])

        # Job must be deleted from queue and present in history
        self.assertIsNone(self.job_repo.get_by_id(BackgroundJob, job.id))
        history_entry = (
            self.session.execute(
                select(BackgroundJobHistory).where(
                    BackgroundJobHistory.job == "cleanup"
                )
            )
            .scalars()
            .first()
        )
        self.assertIsNotNone(history_entry)

    def test_process_link_update_data_job(self):
        """JobExecutor processes link-update-data task and updates timestamp."""
        entry = self.entry_repo.add_entry(
            link="https://example.com/item", title="Old Item"
        )
        entry_id = entry.id

        job = self.job_repo.enqueue_job(
            job="link-update-data",
            subject=str(entry_id),
            priority=1,
            enabled=True,
        )

        executor = JobExecutor(session=self.session, auto_refresh_sources=False)
        result = executor.process_one(session=self.session)

        self.assertIsNotNone(result)
        self.assertTrue(result["success"])
        self.assertEqual(result["job_id"], job.id)

        # Job completed and archived
        self.assertIsNone(self.job_repo.get_by_id(BackgroundJob, job.id))

    def test_process_source_job_success(self):
        """JobExecutor processes process-source task for an existing source."""
        source = self.source_repo.add_source(
            url="https://example.com/rss",
            title="Sample RSS",
            source_type="RSS",
            enabled=True,
        )

        job = self.job_repo.enqueue_job(
            job="process-source",
            subject=str(source.id),
            priority=1,
            enabled=True,
        )

        executor = JobExecutor(session=self.session, auto_refresh_sources=False)

        with patch(
            "yafr.services.source_service.SourceService.fetch_source"
        ) as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "status": "completed",
                "message": "Fetched 5 entries",
            }
            result = executor.process_one(session=self.session)

            self.assertTrue(result["success"])
            self.assertEqual(result["job_id"], job.id)
            mock_fetch.assert_called_once_with(source.id, session=self.session)

        # Job completed and archived
        self.assertIsNone(self.job_repo.get_by_id(BackgroundJob, job.id))

    def test_process_source_job_failure_retry(self):
        """Job failure records error and disables job after reaching max_retries."""
        job = self.job_repo.enqueue_job(
            job="process-source",
            subject="99999",  # Non-existent source ID
            priority=1,
            enabled=True,
        )

        executor = JobExecutor(
            session=self.session, max_retries=2, auto_refresh_sources=False
        )

        # First failure
        res1 = executor.process_one(session=self.session)
        self.assertFalse(res1["success"])
        updated_job = self.job_repo.get_by_id(BackgroundJob, job.id)
        self.assertEqual(updated_job.errors, 1)
        self.assertTrue(updated_job.enabled)

        # Second failure -> reaches max_retries=2 -> disabled
        res2 = executor.process_one(session=self.session)
        self.assertFalse(res2["success"])
        updated_job = self.job_repo.get_by_id(BackgroundJob, job.id)
        self.assertEqual(updated_job.errors, 2)
        self.assertFalse(updated_job.enabled)

        # No more pending jobs (disabled job is skipped)
        res3 = executor.process_one(session=self.session)
        self.assertIsNone(res3)

    def test_empty_queue_fallback_to_outdated_source(self):
        """When queue is empty, auto-refreshes oldest outdated source."""
        source = self.source_repo.add_source(
            url="https://example.com/outdated.xml",
            title="Outdated Feed",
            source_type="RSS",
            enabled=True,
        )
        self.source_repo.update_operational_data(
            source.id,
            date_fetched=datetime.now(timezone.utc) - timedelta(hours=3),
        )

        executor = JobExecutor(session=self.session, auto_refresh_sources=True)

        with patch(
            "yafr.services.source_service.SourceService.fetch_source"
        ) as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "status": "completed",
                "message": "Auto-refreshed",
            }
            result = executor.process_one(session=self.session)

            self.assertIsNotNone(result)
            self.assertEqual(result["job_type"], "source-auto-refresh")
            self.assertEqual(result["subject"], source.url)
            self.assertTrue(result["success"])
            mock_fetch.assert_called_once_with(source.id, session=self.session)

    def test_run_loop_with_max_jobs(self):
        """run_loop terminates cleanly after executing max_jobs."""
        self.job_repo.enqueue_job(job="cleanup", subject="1")
        self.job_repo.enqueue_job(job="cleanup", subject="2")
        self.job_repo.enqueue_job(job="cleanup", subject="3")

        executor = JobExecutor(session=self.session, auto_refresh_sources=False)
        executed = executor.run_loop(interval=0.01, max_jobs=2)

        self.assertEqual(executed, 2)
        self.assertEqual(self.job_repo.count_jobs(), 1)


class TestProcessJobsScriptCLI(unittest.TestCase):
    """
    Test suite for process_jobs.py standalone CLI entrypoint.
    """

    def test_process_jobs_cli_help(self):
        """process_jobs.py --help exits with 0."""
        cmd = [sys.executable, "process_jobs.py", "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Background Task Processor", result.stdout)
        self.assertIn("--once", result.stdout)
        self.assertIn("--interval", result.stdout)

    def test_process_jobs_cli_once_mode(self):
        """process_jobs.py --once processes one job and terminates with code 0."""
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            init_db(temp_db.name, sync_schema=True)
            sess = get_session()
            repo = JobRepository(sess)
            repo.enqueue_job(job="cleanup", subject="cli-test", priority=1)
            close_session()

            cmd = [
                sys.executable,
                "process_jobs.py",
                "--db",
                temp_db.name,
                "--once",
                "--no-refresh-sources",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("[OK]", result.stdout)
            self.assertIn("cleanup", result.stdout)


if __name__ == "__main__":
    unittest.main()

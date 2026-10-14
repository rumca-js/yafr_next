"""
Unit and integration tests for WebToolsWrapper and SourceService integration.
"""

from datetime import datetime, timezone
import hashlib
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import select
from webtoolkit import BaseUrl, RemoteUrl
from webtoolkit.response import PageResponseObject
from linkarchivetools.model.definitions import (
    ConfigurationEntry,
    LinkDataModel,
    SourceOperationalData,
    SourcesTable,
)
from yafr.app import create_app
from yafr.db import (
    ConfigRepository,
    SourceRepository,
    close_session,
    get_session,
)
from yafr.services.source_service import SourceService
from yafr.services.webtools_service import (
    WebToolkitWrapper,
    WebToolsService,
    WebToolsWrapper,
    create_url,
    fetch_response,
    fetch_text,
)


class TestWebToolsWrapper(unittest.TestCase):
    """
    Test suite for WebToolsWrapper class and helpers.
    """

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": ":memory:",
                "SECRET_KEY": "test-key-webtools",
            }
        )
        self.session = get_session()
        self.config_repo = ConfigRepository(self.session)
        # Ensure clean config
        self.config = self.config_repo.get_config()
        self.config.remote_webtools_server_location = None
        self.session.commit()

    def tearDown(self):
        close_session()

    def test_default_uses_base_url_when_remote_not_configured(self):
        """
        When remote_webtools_server_location is None/empty, WebToolsWrapper uses BaseUrl.
        """
        wrapper = WebToolsWrapper(url="https://example.com/rss", session=self.session)
        self.assertFalse(wrapper.is_remote)
        self.assertIsNone(wrapper.remote_server_location)
        self.assertIsInstance(wrapper.url_handler, BaseUrl)

    def test_uses_remote_url_when_remote_configured_in_database(self):
        """
        When remote_webtools_server_location is set in DB, WebToolsWrapper uses RemoteUrl.
        """
        self.config.remote_webtools_server_location = "http://192.168.0.200:3000"
        self.session.commit()

        wrapper = WebToolsWrapper(url="https://example.com/rss", session=self.session)
        self.assertTrue(wrapper.is_remote)
        self.assertEqual(wrapper.remote_server_location, "http://192.168.0.200:3000")
        self.assertIsInstance(wrapper.url_handler, RemoteUrl)
        self.assertEqual(
            wrapper.url_handler.remote_server_location, "http://192.168.0.200:3000"
        )

    def test_explicit_remote_server_location_parameter(self):
        """
        Explicit remote_server_location parameter overrides DB configuration.
        """
        self.config.remote_webtools_server_location = "http://db-server:3000"
        self.session.commit()

        wrapper = WebToolsWrapper(
            url="https://example.com/rss",
            remote_server_location="http://custom-server:8080",
            session=self.session,
        )
        self.assertTrue(wrapper.is_remote)
        self.assertEqual(wrapper.remote_server_location, "http://custom-server:8080")
        self.assertIsInstance(wrapper.url_handler, RemoteUrl)

    def test_explicit_use_remote_false_forces_base_url(self):
        """
        Setting use_remote=False forces BaseUrl even when remote is configured.
        """
        self.config.remote_webtools_server_location = "http://192.168.0.200:3000"
        self.session.commit()

        wrapper = WebToolsWrapper(
            url="https://example.com/rss",
            use_remote=False,
            session=self.session,
        )
        self.assertFalse(wrapper.is_remote)
        self.assertIsNone(wrapper.remote_server_location)
        self.assertIsInstance(wrapper.url_handler, BaseUrl)

    def test_explicit_empty_remote_server_location_forces_base_url(self):
        """
        Passing remote_server_location='' disables remote and uses BaseUrl.
        """
        wrapper = WebToolsWrapper(
            url="https://example.com/rss",
            remote_server_location="",
            session=self.session,
        )
        self.assertFalse(wrapper.is_remote)
        self.assertIsNone(wrapper.remote_server_location)
        self.assertIsInstance(wrapper.url_handler, BaseUrl)

    def test_create_url_factory_returns_base_or_remote_url(self):
        """
        create_url helper returns BaseUrl or RemoteUrl instance.
        """
        # BaseUrl case
        h1 = create_url("https://example.com/feed", session=self.session)
        self.assertIsInstance(h1, BaseUrl)

        # RemoteUrl case
        h2 = create_url(
            "https://example.com/feed",
            remote_server_location="http://127.0.0.1:3000",
            session=self.session,
        )
        self.assertIsInstance(h2, RemoteUrl)

    def test_get_response_and_get_text_with_base_url(self):
        """
        Tests BaseUrl get_response and get_text logic using mock response.
        """
        wrapper = WebToolsWrapper(url="https://example.com/rss", session=self.session)
        sample_rss = "<rss><channel><title>Example</title></channel></rss>"
        mock_response = PageResponseObject(
            url="https://example.com/rss",
            status_code=200,
            text=sample_rss,
            binary=sample_rss.encode("utf-8"),
        )

        with patch.object(
            wrapper.url_handler, "get_response", return_value=mock_response
        ):
            resp = wrapper.get_response()
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get_status_code(), 200)
            self.assertTrue(wrapper.is_valid())
            self.assertEqual(wrapper.get_status_code(), 200)
            self.assertEqual(wrapper.get_text(), sample_rss)
            self.assertEqual(wrapper.get_binary(), sample_rss.encode("utf-8"))

    def test_get_response_and_get_text_with_remote_url(self):
        """
        Tests RemoteUrl get_response and get_text logic using mock response.
        """
        wrapper = WebToolsWrapper(
            url="https://example.com/rss",
            remote_server_location="http://192.168.0.200:3000",
            session=self.session,
        )
        sample_rss = "<rss><channel><title>Remote Feed</title></channel></rss>"
        mock_response = PageResponseObject(
            url="https://example.com/rss",
            status_code=200,
            text=sample_rss,
            binary=sample_rss.encode("utf-8"),
        )

        with patch.object(
            wrapper.url_handler, "get_response", return_value=mock_response
        ):
            self.assertTrue(wrapper.is_remote)
            resp = wrapper.get_response()
            self.assertIsNotNone(resp)
            self.assertEqual(wrapper.get_text(), sample_rss)

    def test_convenience_functions(self):
        """
        Tests fetch_text and fetch_response convenience helpers.
        """
        sample_text = "Feed Content Here"
        mock_response = PageResponseObject(
            url="https://example.com/test",
            status_code=200,
            text=sample_text,
        )

        with patch.object(BaseUrl, "get_response", return_value=mock_response):
            text = fetch_text("https://example.com/test", session=self.session)
            self.assertEqual(text, sample_text)

            resp = fetch_response("https://example.com/test", session=self.session)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get_status_code(), 200)

    def test_aliases_are_identical(self):
        """
        WebToolkitWrapper and WebToolsService are aliases to WebToolsWrapper.
        """
        self.assertIs(WebToolkitWrapper, WebToolsWrapper)
        self.assertIs(WebToolsService, WebToolsWrapper)


class TestSourceServiceWithWrapper(unittest.TestCase):
    """
    Integration tests verifying SourceService uses WebToolsWrapper.
    """

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": ":memory:",
                "SECRET_KEY": "test-key-source-service",
            }
        )
        self.session = get_session()
        self.source_repo = SourceRepository(self.session)
        self.source = self.source_repo.add_source(
            url="https://example.com/feed.xml",
            title="Test Feed",
            source_type="RSS",
            enabled=True,
        )

    def tearDown(self):
        close_session()

    def test_fetch_source_success_creates_entries(self):
        """
        SourceService._execute_fetch downloads through WebToolsWrapper and creates LinkDataModel rows.
        """
        sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <link>https://example.com</link>
            <item>
              <title>Entry Number One</title>
              <link>https://example.com/entry-1</link>
              <description>First description</description>
            </item>
            <item>
              <title>Entry Number Two</title>
              <link>https://example.com/entry-2</link>
              <description>Second description</description>
            </item>
          </channel>
        </rss>"""

        mock_resp = PageResponseObject(
            url=self.source.url,
            status_code=200,
            text=sample_rss,
            binary=sample_rss.encode("utf-8"),
        )

        with patch.object(BaseUrl, "get_response", return_value=mock_resp):
            res = SourceService.fetch_source(self.source.id, session=self.session)
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("entries_added"), 2)

            # Verify in DB
            entries = (
                self.session.execute(
                    select(LinkDataModel).where(
                        LinkDataModel.source_id == self.source.id
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(len(entries), 2)
            links = [e.link for e in entries]
            self.assertIn("https://example.com/entry-1", links)
            self.assertIn("https://example.com/entry-2", links)

            # Verify operational data
            op_data = self.session.execute(
                select(SourceOperationalData).where(
                    SourceOperationalData.source_id == self.source.id
                )
            ).scalar_one()
            self.assertEqual(op_data.number_of_entries, 2)
            self.assertEqual(op_data.consecutive_errors, 0)
            self.assertIsNotNone(op_data.page_hash)

    def test_fetch_source_unchanged_hash_skips_parsing(self):
        """
        When hash matches previous fetch, SourceService returns status='unchanged'.
        """
        sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Unchanged Feed</title>
            <item>
              <title>Static Item</title>
              <link>https://example.com/static</link>
            </item>
          </channel>
        </rss>"""

        content_bytes = sample_rss.encode("utf-8")
        page_hash = hashlib.sha256(content_bytes).digest()

        # Update existing op_data with this page_hash
        op_data = (
            self.session.execute(
                select(SourceOperationalData).where(
                    SourceOperationalData.source_id == self.source.id
                )
            )
            .scalars()
            .first()
        )
        if op_data is None:
            op_data = SourceOperationalData(source_id=self.source.id)
            self.session.add(op_data)
        op_data.page_hash = page_hash
        op_data.body_hash = page_hash
        op_data.consecutive_errors = 0
        op_data.number_of_entries = 1
        self.session.commit()

        mock_resp = PageResponseObject(
            url=self.source.url,
            status_code=200,
            text=sample_rss,
            binary=content_bytes,
        )

        with patch.object(BaseUrl, "get_response", return_value=mock_resp):
            res = SourceService.fetch_source(self.source.id, session=self.session)
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("status"), "unchanged")
            self.assertEqual(res.get("entries_added"), 0)

    def test_fetch_source_network_error_tracks_consecutive_errors(self):
        """
        When WebToolsWrapper returns invalid response, consecutive_errors increments.
        """
        mock_resp = PageResponseObject(
            url=self.source.url,
            status_code=500,
            text=None,
        )
        mock_resp.add_error("Internal Server Error")

        with patch.object(BaseUrl, "get_response", return_value=mock_resp):
            res = SourceService.fetch_source(self.source.id, session=self.session)
            self.assertFalse(res.get("success"))
            self.assertEqual(res.get("status"), "error")

            op_data = self.session.execute(
                select(SourceOperationalData).where(
                    SourceOperationalData.source_id == self.source.id
                )
            ).scalar_one()
            self.assertEqual(op_data.consecutive_errors, 1)


if __name__ == "__main__":
    unittest.main()

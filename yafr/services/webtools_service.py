"""
WebTools and WebToolkit Network Service Wrapper for YAFR.

Provides a unified interface for web network operations utilizing webtoolkit's
BaseUrl and RemoteUrl classes. Handles automatic detection of remote webtools
server location from the application configuration, falling back to local BaseUrl crawling.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union
import warnings
from bs4 import MarkupResemblesLocatorWarning
from sqlalchemy.orm import Session
import webtoolkit
from webtoolkit import BaseUrl, RemoteUrl

# Suppress BeautifulSoup markup locator warning from brutefeedparser/webtoolkit
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# Apply webtoolkit email reader import bug workaround (ARCHITECTURE.md section 3.4)
if "webtoolkit.utils" in sys.modules and "utils" not in sys.modules:
    sys.modules["utils"] = sys.modules["webtoolkit.utils"]
elif hasattr(webtoolkit, "utils") and "utils" not in sys.modules:
    sys.modules["utils"] = webtoolkit.utils

logger = logging.getLogger(__name__)


class WebToolsWrapper:
    """
    Wrapper around webtoolkit network classes (BaseUrl and RemoteUrl).

    If remote webtools is configured (via remote_webtools_server_location in
    configurationentry or explicit parameter), RemoteUrl is used for network
    operations. Otherwise, local BaseUrl is used.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        remote_server_location: Optional[str] = None,
        session: Optional[Session] = None,
        use_remote: Optional[bool] = None,
        timeout_s: Optional[int] = None,
    ) -> None:
        """
        Initializes the WebToolsWrapper.

        :param url: URL to fetch or process.
        :param remote_server_location: Explicit remote webtools server URL (e.g. 'http://127.0.0.1:3000').
                                       If None, automatically retrieved from database configuration.
                                       If empty string '', disables remote webtools.
        :param session: Optional active database Session for configuration lookup.
        :param use_remote: Explicit flag to enable/disable remote webtools.
                           If False, forces BaseUrl. If True, forces RemoteUrl.
        :param timeout_s: Optional request timeout in seconds.
        """
        self.url = url
        self.session = session
        self.timeout_s = timeout_s
        self._response: Optional[Any] = None

        # Resolve whether to use RemoteUrl or BaseUrl
        self.remote_server_location = self._determine_remote_location(
            remote_server_location=remote_server_location,
            use_remote=use_remote,
            session=session,
        )
        self.is_remote = bool(self.remote_server_location)

        # Instantiate underlying webtoolkit URL handler if url is provided
        self.url_handler: Optional[Union[BaseUrl, RemoteUrl]] = None
        if self.url:
            self.url_handler = self._create_handler(
                url=self.url,
                remote_server_location=self.remote_server_location,
                timeout_s=self.timeout_s,
            )

    @classmethod
    def _determine_remote_location(
        cls,
        remote_server_location: Optional[str] = None,
        use_remote: Optional[bool] = None,
        session: Optional[Session] = None,
    ) -> Optional[str]:
        """
        Determines the effective remote server location based on parameters,
        database configuration, and environment variables.
        """
        if use_remote is False:
            return None

        # If explicitly passed as string
        if remote_server_location is not None:
            cleaned = remote_server_location.strip()
            return cleaned if cleaned else None

        # If use_remote is False, don't query config
        resolved = cls.resolve_remote_server_location(session=session)
        if use_remote is True and not resolved:
            # Caller specifically asked for remote but none was configured;
            # fallback to default localhost port if strictly needed or return None
            return resolved

        return resolved

    @classmethod
    def resolve_remote_server_location(
        cls, session: Optional[Session] = None
    ) -> Optional[str]:
        """
        Looks up the active remote_webtools_server_location from database configuration
        or environment variables.
        """
        # 1. Attempt database lookup
        try:
            from yafr.db.config_repository import ConfigRepository

            if session is not None:
                repo = ConfigRepository(session=session)
                config = repo.get_config()
                if config and config.remote_webtools_server_location:
                    loc = config.remote_webtools_server_location.strip()
                    if loc:
                        return loc
            else:
                from yafr.db.session import session_scope

                with session_scope() as scoped_session:
                    repo = ConfigRepository(session=scoped_session)
                    config = repo.get_config()
                    if config and config.remote_webtools_server_location:
                        loc = config.remote_webtools_server_location.strip()
                        if loc:
                            return loc
        except Exception as exc:
            logger.debug(
                "Unable to retrieve remote_webtools_server_location from DB: %s", exc
            )

        # 2. Attempt environment variable fallback
        env_loc = os.environ.get("REMOTE_WEBTOOLS_SERVER_LOCATION") or os.environ.get(
            "WEBTOOLS_SERVER_LOCATION"
        )
        if env_loc and env_loc.strip():
            return env_loc.strip()

        return None

    @classmethod
    def is_remote_enabled(cls, session: Optional[Session] = None) -> bool:
        """
        Returns True if remote webtools is configured and enabled.
        """
        return cls.resolve_remote_server_location(session=session) is not None

    @classmethod
    def _create_handler(
        cls,
        url: str,
        remote_server_location: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> Union[BaseUrl, RemoteUrl]:
        """
        Instantiates either RemoteUrl or BaseUrl based on remote_server_location.
        """
        cleaned_url = url.strip()
        if remote_server_location:
            logger.debug(
                "Using RemoteUrl(%s) via remote server: %s",
                cleaned_url,
                remote_server_location,
            )
            return RemoteUrl(
                url=cleaned_url,
                remote_server_location=remote_server_location,
            )
        else:
            logger.debug("Using BaseUrl(%s)", cleaned_url)
            handler = BaseUrl(url=cleaned_url)
            if timeout_s and hasattr(handler, "request") and handler.request:
                handler.request.timeout_s = timeout_s
            return handler

    @classmethod
    def create_url(
        cls,
        url: str,
        remote_server_location: Optional[str] = None,
        session: Optional[Session] = None,
        use_remote: Optional[bool] = None,
        timeout_s: Optional[int] = None,
    ) -> Union[BaseUrl, RemoteUrl]:
        """
        Factory method returning a webtoolkit RemoteUrl or BaseUrl instance.

        If remote webtools is used, RemoteUrl is returned; otherwise BaseUrl.
        """
        effective_loc = cls._determine_remote_location(
            remote_server_location=remote_server_location,
            use_remote=use_remote,
            session=session,
        )
        return cls._create_handler(
            url=url,
            remote_server_location=effective_loc,
            timeout_s=timeout_s,
        )

    def get_response(self) -> Optional[Any]:
        """
        Fetches and returns the PageResponseObject from the underlying handler.

        Caches the response instance on self._response.
        """
        if self._response is not None:
            return self._response

        if not self.url_handler:
            if not self.url:
                raise ValueError("No URL specified for WebToolsWrapper.")
            self.url_handler = self._create_handler(
                url=self.url,
                remote_server_location=self.remote_server_location,
                timeout_s=self.timeout_s,
            )

        try:
            self._response = self.url_handler.get_response()
            return self._response
        except Exception as exc:
            logger.warning("Error fetching response for %s: %s", self.url, exc)
            return None

    def get_text(self) -> Optional[str]:
        """
        Fetches the response text.

        Uses BaseUrl(url=link).get_response().get_text() or
        RemoteUrl(url=link, ...).get_text() / .get_response().get_text().
        """
        # If RemoteUrl, try direct get_text() first
        if self.is_remote and hasattr(self.url_handler, "get_text"):
            try:
                text = self.url_handler.get_text()
                if text:
                    return text
            except Exception as exc:
                logger.debug("RemoteUrl.get_text() failed: %s", exc)

        # BaseUrl(url=link).get_response().get_text() pattern
        resp = self.get_response()
        if resp is not None:
            try:
                return resp.get_text()
            except Exception as exc:
                logger.debug("Failed to extract text from response: %s", exc)

        return None

    def get_binary(self) -> Optional[bytes]:
        """
        Retrieves the binary content bytes from the response.
        """
        resp = self.get_response()
        if resp is not None:
            try:
                binary = resp.get_binary()
                if binary is not None:
                    return binary
            except Exception:
                pass

        # Fallback: encode text if available
        text = self.get_text()
        if text is not None:
            return text.encode("utf-8", errors="replace")

        return None

    def get_status_code(self) -> Optional[int]:
        """
        Returns the HTTP status code of the response.
        """
        resp = self.get_response()
        if resp is not None and hasattr(resp, "get_status_code"):
            return resp.get_status_code()
        return None

    def is_valid(self) -> bool:
        """
        Returns True if the response was successful and valid.
        """
        resp = self.get_response()
        if resp is not None and hasattr(resp, "is_valid"):
            return bool(resp.is_valid())
        return False

    def get_entries(self) -> List[Dict[str, Any]]:
        """
        Extracts feed entries if available directly from the handler or parses text as RSS.
        """
        if self.url_handler and hasattr(self.url_handler, "get_entries"):
            try:
                entries = self.url_handler.get_entries()
                if entries:
                    return list(entries)
            except Exception as exc:
                logger.debug("Handler get_entries() failed: %s", exc)

        text = self.get_text()
        if text and self.url:
            try:
                rss_page = webtoolkit.RssPage(self.url, text)
                if rss_page.is_valid():
                    return list(rss_page.get_entries())
            except Exception as exc:
                logger.debug("RssPage parsing failed: %s", exc)

        return []

    @classmethod
    def fetch_text(
        cls,
        url: str,
        remote_server_location: Optional[str] = None,
        session: Optional[Session] = None,
        use_remote: Optional[bool] = None,
        timeout_s: Optional[int] = None,
    ) -> Optional[str]:
        """
        Convenience class method to fetch URL text in one call.
        """
        wrapper = cls(
            url=url,
            remote_server_location=remote_server_location,
            session=session,
            use_remote=use_remote,
            timeout_s=timeout_s,
        )
        return wrapper.get_text()

    @classmethod
    def fetch_response(
        cls,
        url: str,
        remote_server_location: Optional[str] = None,
        session: Optional[Session] = None,
        use_remote: Optional[bool] = None,
        timeout_s: Optional[int] = None,
    ) -> Optional[Any]:
        """
        Convenience class method to fetch PageResponseObject in one call.
        """
        wrapper = cls(
            url=url,
            remote_server_location=remote_server_location,
            session=session,
            use_remote=use_remote,
            timeout_s=timeout_s,
        )
        return wrapper.get_response()


# Aliases for convenience and architectural consistency
WebToolkitWrapper = WebToolsWrapper
WebToolsService = WebToolsWrapper

# Convenience functional helpers
create_url = WebToolsWrapper.create_url
fetch_text = WebToolsWrapper.fetch_text
fetch_response = WebToolsWrapper.fetch_response

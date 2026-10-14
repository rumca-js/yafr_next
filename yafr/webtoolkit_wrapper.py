"""
Webtoolkit wrapper module export for YAFR.

Re-exports WebToolsWrapper, WebToolkitWrapper, and convenience functions from
yafr.services.webtools_service.
"""

from yafr.services.webtools_service import (
    WebToolkitWrapper,
    WebToolsService,
    WebToolsWrapper,
    check_remote_status,
    create_url,
    fetch_response,
    fetch_text,
)

__all__ = [
    "WebToolsWrapper",
    "WebToolkitWrapper",
    "WebToolsService",
    "check_remote_status",
    "create_url",
    "fetch_text",
    "fetch_response",
]

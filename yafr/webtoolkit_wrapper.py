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
    fetch_author,
    fetch_content_links,
    fetch_date_published,
    fetch_description,
    fetch_response,
    fetch_text,
    fetch_title,
)

__all__ = [
    "WebToolsWrapper",
    "WebToolkitWrapper",
    "WebToolsService",
    "check_remote_status",
    "create_url",
    "fetch_text",
    "fetch_response",
    "fetch_title",
    "fetch_description",
    "fetch_date_published",
    "fetch_author",
    "fetch_content_links",
]

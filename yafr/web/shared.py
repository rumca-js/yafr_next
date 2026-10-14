"""
Shared helpers, constants, and utilities for YAFR web views.
"""

from typing import Any, Dict, Optional
from flask import jsonify, Response


# Display Styles
DISPLAY_STYLE_LIGHT = "style-light"
DISPLAY_STYLE_DARK = "style-dark"

# Display Types (Layouts)
DISPLAY_TYPE_STANDARD = "standard"
DISPLAY_TYPE_GALLERY = "gallery"
DISPLAY_TYPE_SEARCH_ENGINE = "search-engine"
DISPLAY_TYPE_CONTENT_CENTRIC = "content-centric"
DISPLAY_TYPE_LINKS_ONLY = "links-only"

# Predefined Filters for Entries
ENTRY_FILTERS = [
    {"id": "date_published", "name": "by Date published", "default": True},
    {"id": "read_later", "name": "Read Later", "default": False},
    {"id": "visited", "name": "Visited", "default": False},
    {"id": "votes", "name": "by Votes", "default": False},
    {"id": "visits", "name": "by Visits", "default": False},
]


def api_response(
    success: bool = True,
    data: Optional[Any] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    status_code: int = 200,
) -> Response:
    """
    Standardized JSON API response wrapper.

    :param success: Whether the operation succeeded
    :param data: Optional payload data
    :param message: Optional human-readable message
    :param error: Optional error description
    :param status_code: HTTP status code
    :return: Flask JSON response object
    """
    payload: Dict[str, Any] = {"success": success}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    if error is not None:
        payload["error"] = error

    response = jsonify(payload)
    response.status_code = status_code
    return response


def get_shared_context() -> Dict[str, Any]:
    """
    Returns application-wide context variables injected into templates.
    """
    return {
        "app_name": "YAFR",
        "app_tagline": "Yet Another Feed Reader",
        "entry_filters": ENTRY_FILTERS,
        "active_theme": DISPLAY_STYLE_LIGHT,
        "badges": {
            "sources_outdated": 0,
            "sources_errors": 0,
            "jobs_errors": 0,
        },
    }

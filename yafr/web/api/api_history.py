"""
History and Autocomplete REST / JSON API Endpoints.
"""

from flask import Blueprint, request
from yafr.db import HistoryRepository, get_session
from yafr.web.shared import api_response

api_history_bp = Blueprint("api_history", __name__, url_prefix="/api/history")


@api_history_bp.route("/autocomplete", methods=["GET"])
def autocomplete():
    """
    Returns search query suggestions matching the prefix parameter 'q'.
    """
    prefix = request.args.get("q", "").strip()
    session = get_session()
    repo = HistoryRepository(session)
    suggestions = repo.get_recent_searches(
        query_prefix=prefix if prefix else None, limit=10
    )
    return api_response(success=True, data={"suggestions": suggestions})

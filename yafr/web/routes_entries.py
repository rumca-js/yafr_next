"""
Entry routes and search views controller.
"""

from flask import Blueprint, render_template, request
from yafr.web.shared import ENTRY_FILTERS

entries_bp = Blueprint("entries", __name__)


@entries_bp.route("/")
@entries_bp.route("/entries")
def search_view():
    """
    Renders EntriesListView (Google-like search page).

    - If query parameter 'q' is empty/missing: displays large centered search input.
    - If 'q' is provided: displays search widget at top with search results container.
    """
    query = request.args.get("q", "").strip()
    active_filter = request.args.get("filter", "date_published")

    has_query = bool(query)

    # Placeholder results structure for search results
    entries = []

    return render_template(
        "entries/list.html",
        query=query,
        has_query=has_query,
        active_filter=active_filter,
        filters=ENTRY_FILTERS,
        entries=entries,
        total_results=len(entries),
    )

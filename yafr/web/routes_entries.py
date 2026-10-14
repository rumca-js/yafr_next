"""
Entry routes and search views controller.
"""

import math
from flask import Blueprint, render_template, request
from sqlalchemy import select
from linkarchivetools.model.definitions import SocialData, SourcesTable
from yafr.db import ConfigRepository, EntryRepository, HistoryRepository, get_session
from yafr.search import FilterRegistry, SearchParser, SearchQueryBuilder

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
    page = max(1, request.args.get("page", 1, type=int))

    has_query = bool(query)

    session = get_session()
    config_repo = ConfigRepository(session)
    history_repo = HistoryRepository(session)
    entry_repo = EntryRepository(session)

    config = config_repo.get_config()
    display_type = request.args.get("display", config.display_type or "gallery")
    per_page = int(config.links_per_page or 25)
    offset = (page - 1) * per_page

    entries = []
    total_results = 0

    if has_query:
        # Save query to user search history for autocomplete
        history_repo.add_search(
            query, max_limit=int(config.max_number_of_user_search or 300)
        )

        # Parse user query using AST grammar
        parsed_query = SearchParser.parse(query)

        # Execute search with filters and sorting
        entries, total_results = SearchQueryBuilder.execute_search(
            session=session,
            parsed_query=parsed_query,
            filter_id=active_filter,
            limit=per_page,
            offset=offset,
        )

    total_pages = (
        max(1, math.ceil(total_results / per_page)) if total_results > 0 else 1
    )
    filters = FilterRegistry.get_available_filters(session)

    # Attach sources, social metrics, tags, and status mappings for template rendering
    entry_ids = [e.id for e in entries]
    read_later_ids = set()
    visited_ids = set()
    tags_map = {}
    sources_map = {}
    social_map = {}

    if entry_ids:
        read_later_ids = history_repo.get_read_later_entry_ids()
        visited_ids = history_repo.get_visited_entry_ids()

        for e in entries:
            tags_map[e.id] = entry_repo.get_tags(e.id)

        source_ids = {e.source_id for e in entries if e.source_id}
        if source_ids:
            sources = (
                session.execute(
                    select(SourcesTable).where(SourcesTable.id.in_(source_ids))
                )
                .scalars()
                .all()
            )
            sources_map = {s.id: s for s in sources}

        social_records = (
            session.execute(
                select(SocialData).where(SocialData.entry_id.in_(entry_ids))
            )
            .scalars()
            .all()
        )
        social_map = {s.entry_id: s for s in social_records}

    return render_template(
        "entries/list.html",
        query=query,
        has_query=has_query,
        active_filter=active_filter,
        filters=filters,
        entries=entries,
        total_results=total_results,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        display_type=display_type,
        read_later_ids=read_later_ids,
        visited_ids=visited_ids,
        tags_map=tags_map,
        sources_map=sources_map,
        social_map=social_map,
    )

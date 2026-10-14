"""
Predefined and Dynamic Search Filters for YAFR.

Encapsulates system filters (by Date published, Read Later, Visited,
by Votes, by Visits) and manages custom search views from SQLite searchview table.
"""

from dataclasses import dataclass
import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import SearchView
from yafr.db import get_session

logger = logging.getLogger(__name__)


@dataclass
class SearchFilter:
    """
    Representation of a selectable search filter option.

    :param id: Unique filter identifier string
    :param name: Human-readable display label
    :param is_default: Whether this filter is the default selection
    :param hover_text: Optional tooltip description
    """

    id: str
    name: str
    is_default: bool = False
    hover_text: Optional[str] = None


SYSTEM_FILTERS = [
    SearchFilter(
        id="date_published",
        name="by Date published",
        is_default=True,
        hover_text="Order entries by publication date descending",
    ),
    SearchFilter(
        id="read_later",
        name="Read Later",
        is_default=False,
        hover_text="Show only entries saved for reading later",
    ),
    SearchFilter(
        id="visited",
        name="Visited",
        is_default=False,
        hover_text="Show only entries previously visited",
    ),
    SearchFilter(
        id="votes",
        name="by Votes",
        is_default=False,
        hover_text="Order entries by rating votes descending",
    ),
    SearchFilter(
        id="visits",
        name="by Visits",
        is_default=False,
        hover_text="Order entries by total visit count descending",
    ),
]


class FilterRegistry:
    """
    Registry providing system filters and custom views defined in SQLite.
    """

    @classmethod
    def get_system_filters(cls) -> List[SearchFilter]:
        """
        Returns the core system filters.
        """
        return list(SYSTEM_FILTERS)

    @classmethod
    def get_available_filters(
        cls, session: Optional[Session] = None
    ) -> List[SearchFilter]:
        """
        Retrieves all available filters: predefined system filters combined with
        any custom search views stored in the SQLite searchview table.

        :param session: Optional active database session
        :return: List of SearchFilter instances
        """
        filters = list(SYSTEM_FILTERS)
        try:
            db_session = session or get_session()
            stmt = select(SearchView).order_by(
                SearchView.priority.asc(), SearchView.id.asc()
            )
            custom_views = db_session.execute(stmt).scalars().all()

            for view in custom_views:
                if not any(f.id == f"custom_{view.id}" for f in filters):
                    filters.append(
                        SearchFilter(
                            id=f"custom_{view.id}",
                            name=view.name,
                            is_default=bool(view.default),
                            hover_text=view.hover_text,
                        )
                    )
        except Exception as err:
            logger.debug("Failed to query custom SearchView records: %s", err)

        return filters

    @classmethod
    def get_filter(cls, filter_id: Optional[str]) -> SearchFilter:
        """
        Resolves a filter by ID, falling back to 'date_published' default.

        :param filter_id: Filter ID string
        :return: Matching SearchFilter
        """
        if not filter_id:
            filter_id = "date_published"

        for f in cls.get_system_filters():
            if f.id == filter_id:
                return f

        # Fallback to date_published
        return SYSTEM_FILTERS[0]

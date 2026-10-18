"""
SQLAlchemy Query Builder for YAFR Search Engine.

Translates ParsedQuery AST tokens into indexed SQLAlchemy expressions,
applying operators ('=', '=='), joins for tags and social metrics,
system filters, explicit ordering, and pagination.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from linkarchivetools.model.definitions import (
    EntryCompactedTags,
    EntryVisitHistory,
    LinkDataModel,
    ReadLater,
    SocialData,
)
from yafr.search.parser import ParsedQuery, SearchClause

logger = logging.getLogger(__name__)


class SearchQueryBuilder:
    """
    Compiles search AST tokens into executable SQLAlchemy statements.
    """

    @classmethod
    def build_select(
        cls,
        parsed_query: ParsedQuery,
        filter_id: Optional[str] = "date_published",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Select:
        """
        Builds the primary SELECT statement for matching LinkDataModel entries.

        :param parsed_query: Parsed query AST
        :param filter_id: Active system filter ID ('date_published', 'read_later', etc.)
        :param limit: Maximum rows to return (pagination)
        :param offset: Number of rows to skip (pagination)
        :return: Compiled SQLAlchemy Select statement
        """
        stmt = select(LinkDataModel)
        stmt = cls._apply_clauses(stmt, parsed_query.clauses)
        stmt, applied_order = cls._apply_filter(stmt, filter_id)
        stmt = cls._apply_ordering(stmt, parsed_query.order_by, applied_order)

        if offset is not None and offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        return stmt

    @classmethod
    def build_count(
        cls,
        parsed_query: ParsedQuery,
        filter_id: Optional[str] = "date_published",
    ) -> Select:
        """
        Builds the COUNT statement to calculate total matching results for pagination.

        :param parsed_query: Parsed query AST
        :param filter_id: Active system filter ID
        :return: Compiled SQLAlchemy Select statement returning integer count
        """
        stmt = select(func.count(LinkDataModel.id))
        stmt = cls._apply_clauses(stmt, parsed_query.clauses)
        stmt, _ = cls._apply_filter(stmt, filter_id)
        return stmt

    @classmethod
    def execute_search(
        cls,
        session: Session,
        parsed_query: ParsedQuery,
        filter_id: Optional[str] = "date_published",
        limit: int = 25,
        offset: int = 0,
    ) -> Tuple[List[LinkDataModel], int]:
        """
        Executes search and returns matching entries along with total count.

        :param session: Active database session
        :param parsed_query: Parsed query AST
        :param filter_id: Active filter ID
        :param limit: Results per page
        :param offset: Pagination offset
        :return: Tuple of (list of LinkDataModel entries, total count)
        """
        count_stmt = cls.build_count(parsed_query, filter_id)
        total_count = session.execute(count_stmt).scalar() or 0

        if total_count == 0:
            return [], 0

        select_stmt = cls.build_select(
            parsed_query, filter_id, limit=limit, offset=offset
        )
        entries = list(session.execute(select_stmt).scalars().all())
        return entries, total_count

    @classmethod
    def _apply_clauses(cls, stmt: Select, clauses: List[SearchClause]) -> Select:
        """
        Applies search token predicates to the query statement.
        """
        for clause in clauses:
            field_name = clause.field
            val = clause.value.strip()
            if not val:
                continue

            # Free-text search: matches title or description
            if field_name is None:
                condition = or_(
                    LinkDataModel.title.ilike(f"%{val}%"),
                    LinkDataModel.description.ilike(f"%{val}%"),
                )
                if clause.negated:
                    condition = ~condition
                stmt = stmt.where(condition)
                continue

            # Tag search (subquery on EntryCompactedTags)
            if field_name == "tag":
                clean_tag = val.lstrip("#").lower()
                if clause.operator == "==":
                    tag_stmt = select(EntryCompactedTags.entry_id).where(
                        EntryCompactedTags.tag == clean_tag
                    )
                else:
                    tag_stmt = select(EntryCompactedTags.entry_id).where(
                        EntryCompactedTags.tag.ilike(f"%{clean_tag}%")
                    )

                if clause.negated:
                    stmt = stmt.where(LinkDataModel.id.not_in(tag_stmt))
                else:
                    stmt = stmt.where(LinkDataModel.id.in_(tag_stmt))
                continue

            # Status search
            if field_name == "status":
                if val.lower() == "active":
                    cond = LinkDataModel.manual_status_code == 200
                elif val.lower() == "dead":
                    cond = or_(
                        LinkDataModel.manual_status_code == 400,
                        LinkDataModel.status_code >= 400,
                    )
                else:
                    try:
                        code = int(val)
                        cond = or_(
                            LinkDataModel.manual_status_code == code,
                            LinkDataModel.status_code == code,
                        )
                    except ValueError:
                        continue

                if clause.negated:
                    cond = ~cond
                stmt = stmt.where(cond)
                continue

            # Bookmarked search
            if field_name == "bookmarked":
                val_lower = val.lower()
                is_true = val_lower in ("true", "1", "yes")
                cond = LinkDataModel.bookmarked == is_true
                if clause.negated:
                    cond = ~cond
                stmt = stmt.where(cond)
                continue

            # Standard string columns: title, description, link, author, language
            if hasattr(LinkDataModel, field_name):
                column = getattr(LinkDataModel, field_name)
                if clause.operator == "==":
                    cond = column == val
                else:
                    cond = column.ilike(f"%{val}%")

                if clause.negated:
                    cond = ~cond
                stmt = stmt.where(cond)

        return stmt

    @classmethod
    def _apply_filter(
        cls, stmt: Select, filter_id: Optional[str]
    ) -> Tuple[Select, bool]:
        """
        Applies system filter joins and default sort.
        Returns modified Select and whether an order was applied.
        """
        order_applied = False

        if filter_id == "read_later":
            stmt = stmt.join(ReadLater, ReadLater.entry_id == LinkDataModel.id)
            stmt = stmt.order_by(ReadLater.id.desc())
            order_applied = True

        elif filter_id == "visited":
            stmt = stmt.join(
                EntryVisitHistory,
                (EntryVisitHistory.entry_id == LinkDataModel.id)
                & (EntryVisitHistory.visits > 0),
            )
            stmt = stmt.order_by(
                EntryVisitHistory.date_last_visit.desc().nullslast(),
                EntryVisitHistory.id.desc(),
            )
            order_applied = True

        elif filter_id == "votes":
            stmt = stmt.order_by(
                LinkDataModel.page_rating_votes.desc(),
                LinkDataModel.id.desc(),
            )
            order_applied = True

        elif filter_id == "visits":
            stmt = stmt.order_by(
                LinkDataModel.page_rating_visits.desc(),
                LinkDataModel.id.desc(),
            )
            order_applied = True

        elif filter_id and filter_id.startswith("custom_"):
            from yafr.search.filters import FilterRegistry
            from yafr.search.parser import SearchParser

            view = FilterRegistry.get_search_view(filter_id)
            if view:
                if view.filter_statement:
                    parsed_custom = SearchParser.parse(view.filter_statement)
                    stmt = cls._apply_clauses(stmt, parsed_custom.clauses)
                if view.order_by:
                    stmt = cls._apply_ordering(
                        stmt, view.order_by, filter_order_applied=False
                    )
                    order_applied = True

        elif filter_id == "date_published" or not filter_id:
            stmt = stmt.order_by(
                LinkDataModel.date_published.desc().nullslast(),
                LinkDataModel.id.desc(),
            )
            order_applied = True

        return stmt, order_applied

    @classmethod
    def _apply_ordering(
        cls,
        stmt: Select,
        order_by: Optional[str],
        filter_order_applied: bool,
    ) -> Select:
        """
        Applies explicit ordering directives from search query or custom search view.
        Overrides system filter ordering when specified.
        """
        if not order_by or not order_by.strip():
            if not filter_order_applied:
                # Fallback ordering
                stmt = stmt.order_by(
                    LinkDataModel.date_published.desc().nullslast(),
                    LinkDataModel.id.desc(),
                )
            return stmt

        tokens = [t.strip() for t in order_by.split(",") if t.strip()]
        if not tokens:
            return stmt

        # Clear existing filter ordering if explicit order is specified
        stmt = stmt.order_by(None)
        order_clauses = []
        joined_social = False

        for token in tokens:
            is_asc = token.startswith("+")
            is_explicit_desc = token.startswith("-")
            clean = token.lstrip("-+").strip().lower()

            if clean in ("published", "date_published"):
                order_clauses.append(
                    LinkDataModel.date_published.asc().nullsfirst()
                    if is_asc
                    else LinkDataModel.date_published.desc().nullslast()
                )
            elif clean in ("created", "date_created"):
                order_clauses.append(
                    LinkDataModel.date_created.asc().nullsfirst()
                    if is_asc
                    else LinkDataModel.date_created.desc().nullslast()
                )
            elif clean in ("votes", "page_rating_votes"):
                order_clauses.append(
                    LinkDataModel.page_rating_votes.asc()
                    if is_asc
                    else LinkDataModel.page_rating_votes.desc()
                )
            elif clean in ("rating", "page_rating"):
                order_clauses.append(
                    LinkDataModel.page_rating.asc()
                    if is_asc
                    else LinkDataModel.page_rating.desc()
                )
            elif clean in ("visits", "page_rating_visits", "visit_count"):
                order_clauses.append(
                    LinkDataModel.page_rating_visits.asc()
                    if is_asc
                    else LinkDataModel.page_rating_visits.desc()
                )
            elif clean == "link":
                order_clauses.append(
                    LinkDataModel.link.desc()
                    if is_explicit_desc
                    else LinkDataModel.link.asc()
                )
            elif clean in ("followers", "followers_count"):
                if not joined_social:
                    stmt = stmt.outerjoin(
                        SocialData, SocialData.entry_id == LinkDataModel.id
                    )
                    joined_social = True
                order_clauses.append(
                    SocialData.followers_count.asc().nullsfirst()
                    if is_asc
                    else SocialData.followers_count.desc().nullslast()
                )
            elif clean in ("stars", "socialdata__thumbs_up", "thumbs_up"):
                if not joined_social:
                    stmt = stmt.outerjoin(
                        SocialData, SocialData.entry_id == LinkDataModel.id
                    )
                    joined_social = True
                order_clauses.append(
                    SocialData.stars.asc().nullsfirst()
                    if is_asc
                    else SocialData.stars.desc().nullslast()
                )
            elif clean in ("socialdata__view_count", "views"):
                if not joined_social:
                    stmt = stmt.outerjoin(
                        SocialData, SocialData.entry_id == LinkDataModel.id
                    )
                    joined_social = True
                order_clauses.append(
                    SocialData.views.asc().nullsfirst()
                    if is_asc
                    else SocialData.views.desc().nullslast()
                )

        if order_clauses:
            order_clauses.append(LinkDataModel.id.desc())
            return stmt.order_by(*order_clauses)

        # Fallback to date_published
        return stmt.order_by(
            LinkDataModel.date_published.desc().nullslast(),
            LinkDataModel.id.desc(),
        )

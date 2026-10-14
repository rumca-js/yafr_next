"""
Entry Rules Repository Implementation for YAFR.

Manages URL filtering, blocking, trusting, and auto-tagging rules
configured in the entryrules SQLite table.
"""

import logging
from typing import Any, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import EntryRules
from yafr.db.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RulesRepository(BaseRepository[EntryRules]):
    """
    Data access repository for URL inspection and processing rules.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        super().__init__(session=session)

    def list_rules(
        self,
        enabled_only: bool = False,
        order_by: str = "priority",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[EntryRules]:
        """
        Lists configured entry rules ordered by priority.

        :param enabled_only: If True, only returns active rules
        :param order_by: Sorting field ('priority', 'name', 'id')
        :param limit: Maximum rows to return
        :param offset: Number of rows to skip
        :return: List of EntryRules instances
        """
        stmt = select(EntryRules)
        if enabled_only:
            stmt = stmt.where(EntryRules.enabled == True)

        if order_by == "name":
            stmt = stmt.order_by(EntryRules.rule_name.asc())
        elif order_by == "id":
            stmt = stmt.order_by(EntryRules.id.asc())
        else:
            stmt = stmt.order_by(EntryRules.priority.asc(), EntryRules.id.asc())

        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.session.execute(stmt).scalars().all())

    def get_rule(self, rule_id: int) -> Optional[EntryRules]:
        """
        Retrieves a rule by primary key ID.

        :param rule_id: Rule ID
        :return: EntryRules instance or None
        """
        return self.get_by_id(EntryRules, rule_id)

    def add_rule(
        self,
        rule_name: str,
        trigger_rule_url: str,
        enabled: bool = True,
        priority: int = 0,
        block: bool = False,
        trust: bool = False,
        auto_tag: str = "",
        apply_age_limit: int = 0,
        source_id: Optional[int] = None,
        **kwargs: Any,
    ) -> EntryRules:
        """
        Creates a new entry rule.

        :param rule_name: Human-readable name for the rule
        :param trigger_rule_url: Regex pattern matching candidate URLs
        :param enabled: Whether the rule is actively enforced
        :param priority: Integer priority for execution sequence
        :param block: Whether matching URLs should be blocked
        :param trust: Whether matching URLs are marked trusted
        :param auto_tag: Comma-separated tags to automatically attach
        :param apply_age_limit: Age restriction to apply
        :param source_id: Optional source foreign key scoping this rule
        :return: Persisted EntryRules instance
        """
        rule = EntryRules(
            rule_name=rule_name,
            trigger_rule_url=trigger_rule_url,
            trigger_text="",
            trigger_text_fields="",
            enabled=enabled,
            priority=priority,
            block=block,
            trust=trust,
            auto_tag=auto_tag or "",
            apply_age_limit=apply_age_limit,
            source_id=source_id,
            **kwargs,
        )
        self.session.add(rule)
        self.session.commit()
        return rule

    def update_rule(self, rule_id: int, **kwargs: Any) -> Optional[EntryRules]:
        """
        Updates fields on an existing rule.

        :param rule_id: Rule ID
        :param kwargs: Fields to update
        :return: Updated EntryRules instance or None
        """
        rule = self.get_rule(rule_id)
        if not rule:
            return None

        for key, val in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, val)

        self.session.commit()
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """
        Deletes a rule.

        :param rule_id: Rule ID
        :return: True if deleted, False if not found
        """
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        self.session.delete(rule)
        self.session.commit()
        return True

    def toggle_rule(self, rule_id: int) -> Optional[bool]:
        """
        Toggles enabled state of a rule.

        :param rule_id: Rule ID
        :return: New enabled state or None if not found
        """
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        rule.enabled = not bool(rule.enabled)
        self.session.commit()
        return rule.enabled

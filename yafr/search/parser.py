"""
Search Expression Parser and Lexer for YAFR.

Parses raw user query strings into structured clauses, handling operators
('=' for substring LIKE, '==' for exact match), negation ('!', '-'),
quoted phrases, field-specific targets, and ordering directives.
"""

from dataclasses import dataclass, field
import logging
import re
import shlex
from typing import List, Optional

logger = logging.getLogger(__name__)

# Canonical field name mappings for user-friendly aliases
FIELD_ALIASES = {
    "title": "title",
    "desc": "description",
    "description": "description",
    "link": "link",
    "url": "link",
    "author": "author",
    "channel": "author",
    "lang": "language",
    "language": "language",
    "tag": "tag",
    "tags": "tag",
    "status": "status",
    "bookmark": "bookmarked",
    "bookmarked": "bookmarked",
    "bookmarks": "bookmarked",
}

ORDER_DIRECTIVES = ("order:", "sort:")


@dataclass
class SearchClause:
    """
    Represents a single query predicate.

    :param field: Field to target (None for free-text search matching title/description)
    :param operator: Operator ('=' for substring LIKE, '==' for exact equality)
    :param value: Searched string value
    :param negated: Whether the predicate is inverted (NOT LIKE / !=)
    """

    field: Optional[str]
    operator: str
    value: str
    negated: bool = False


@dataclass
class ParsedQuery:
    """
    Represents the full parsed search query AST.

    :param raw_query: Original user input string
    :param clauses: List of parsed SearchClause filters
    :param order_by: Explicit sort criterion requested in query (e.g. 'published', 'votes')
    """

    raw_query: str
    clauses: List[SearchClause] = field(default_factory=list)
    order_by: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        """Returns True if the query has no search predicates."""
        return len(self.clauses) == 0


class SearchParser:
    """
    Lexer and parser that translates user search syntax into a structured AST.
    """

    @classmethod
    def parse(cls, raw_query: Optional[str]) -> ParsedQuery:
        """
        Parses a user input query string.

        :param raw_query: Raw user input text
        :return: ParsedQuery AST
        """
        if not raw_query or not raw_query.strip():
            return ParsedQuery(raw_query="")

        cleaned = raw_query.strip()
        tokens = cls._tokenize(cleaned)

        clauses: List[SearchClause] = []
        explicit_order: Optional[str] = None

        for token in tokens:
            if not token:
                continue

            # Check for ordering directives: order:votes, sort:published
            lower_token = token.lower()
            if any(lower_token.startswith(prefix) for prefix in ORDER_DIRECTIVES):
                prefix_len = 6 if lower_token.startswith("order:") else 5
                explicit_order = token[prefix_len:].strip().lower()
                continue

            # Check for negation prefix: -term, !term, -field=val, !field=val
            negated = False
            if token.startswith("-") and len(token) > 1:
                negated = True
                token = token[1:]
            elif token.startswith("!") and len(token) > 1:
                negated = True
                token = token[1:]

            # Check for exact match operator '=='
            if "==" in token:
                parts = token.split("==", 1)
                field_name = parts[0].strip().lower()
                val = parts[1].strip()
                canonical_field = FIELD_ALIASES.get(field_name, field_name)
                clauses.append(
                    SearchClause(
                        field=canonical_field,
                        operator="==",
                        value=val,
                        negated=negated,
                    )
                )
                continue

            # Check for substring match operator '=' or ':'
            has_single_eq = "=" in token
            has_colon = (
                ":" in token
                and not token.startswith("http://")
                and not token.startswith("https://")
            )

            if has_single_eq or has_colon:
                separator = "=" if has_single_eq else ":"
                parts = token.split(separator, 1)
                field_name = parts[0].strip().lower()
                val = parts[1].strip()

                if field_name in FIELD_ALIASES:
                    canonical_field = FIELD_ALIASES[field_name]
                    clauses.append(
                        SearchClause(
                            field=canonical_field,
                            operator="=",
                            value=val,
                            negated=negated,
                        )
                    )
                    continue

            # Free-text token (matches title or description)
            clauses.append(
                SearchClause(
                    field=None,
                    operator="=",
                    value=token,
                    negated=negated,
                )
            )

        return ParsedQuery(
            raw_query=cleaned,
            clauses=clauses,
            order_by=explicit_order,
        )

    @classmethod
    def _tokenize(cls, query_str: str) -> List[str]:
        """
        Tokenizes query string respecting quoted strings.
        Gracefully handles unclosed quotes.
        """
        try:
            return shlex.split(query_str, posix=True)
        except ValueError:
            # Handle unclosed quotes by attempting to close them or regex fallback
            try:
                return shlex.split(query_str + '"', posix=True)
            except ValueError:
                return re.findall(r'[^\s"]+|"[^"]*"', query_str)

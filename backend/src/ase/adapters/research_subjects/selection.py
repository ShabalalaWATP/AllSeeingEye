"""Explicit subject routing; never infer upstream search text from a private question."""

import re
from datetime import UTC, datetime
from typing import Any

from ase.adapters.research.feed import search_terms
from ase.domain.research import ResearchFocus, ResearchQuery


def selected(query: ResearchQuery, source_id: str, marker: str) -> bool:
    return (
        query.focus is ResearchFocus.GENERAL
        and (
            source_id in (query.source_ids or ())
            or (query.subject or "").lower().startswith(marker)
        )
        and bool(search_terms(query))
        and "en" in query.languages
    )


def day(value: Any) -> datetime | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def in_window(value: datetime | None, query: ResearchQuery) -> bool:
    return value is not None and query.since <= value < query.until


def doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    identifier = value.removeprefix("https://doi.org/").lower()
    return identifier if re.fullmatch(r"10\.[0-9]{4,9}/[^\s<>\"?#]{1,180}", identifier) else None

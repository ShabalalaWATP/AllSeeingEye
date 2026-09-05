"""Bound keyword collection to a small, polite budget over enabled plans."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from datetime import datetime, timedelta

from ase.domain.collection import CollectionPlan

MAX_WATCHLIST_TERMS = 12
MAX_TERM_LENGTH = 60
MAX_REQUESTS_PER_HOUR = 48
REQUEST_INTERVAL = timedelta(seconds=60)
TERM_INTERVAL = timedelta(minutes=15)


def watchlist_terms(plans: Sequence[CollectionPlan]) -> tuple[str, ...]:
    """Literal phrases, deduplicated across plans, with deterministic bounded selection.

    Quotes and backslashes are removed before quoting the phrase at the RSS boundary,
    so a stored keyword cannot escape its phrase and append Google search operators.
    """
    terms: dict[str, str] = {}
    for plan in plans:
        if not plan.enabled:
            continue
        for raw in plan.search_terms():
            term = " ".join(raw.replace('"', " ").replace(chr(92), " ").split())
            term = "".join(char for char in term if char.isprintable())[:MAX_TERM_LENGTH].strip()
            if term:
                terms.setdefault(term.casefold(), term)
            if len(terms) >= MAX_WATCHLIST_TERMS:
                return tuple(terms.values())
    return tuple(terms.values())


class WatchlistBudget:
    """Reservations count even when upstream fails; configuration changes never reset quota."""

    def __init__(self) -> None:
        self._requests: deque[datetime] = deque()
        self._due: dict[str, datetime] = {}
        self._next_request: datetime | None = None

    def take(self, terms: Sequence[str], now: datetime) -> str | None:
        self._due = {term: self._due.get(term, now) for term in terms}
        while self._requests and self._requests[0] <= now - timedelta(hours=1):
            self._requests.popleft()
        if len(self._requests) >= MAX_REQUESTS_PER_HOUR:
            return None
        if self._next_request is not None and now < self._next_request:
            return None
        due = [term for term in terms if self._due[term] <= now]
        if not due:
            return None
        term = min(due, key=lambda item: self._due[item])
        self._due[term] = now + TERM_INTERVAL
        self._next_request = now + REQUEST_INTERVAL
        self._requests.append(now)
        return term

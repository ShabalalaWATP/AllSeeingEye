"""Pure category retention decisions; the store owns index and stream mutations."""

from collections.abc import Iterable, Mapping
from datetime import datetime

from ase.application.feeds.budgets import VESSEL_POSITION_AGE, RetentionBudget
from ase.application.feeds.position_freshness import satellite_position_expired
from ase.domain.events import Category, Event


def category_removals(
    events: Mapping[str, Event],
    identifiers: Iterable[str],
    category: Category,
    budget: RetentionBudget,
    now: datetime,
) -> tuple[list[str], list[str]]:
    """Select expired IDs and oldest overflow from one consistent category index."""
    cutoff = now - budget.window
    vessel_cutoff = now - VESSEL_POSITION_AGE
    maritime, space = category is Category.MARITIME, category is Category.SPACE
    expired: list[str] = []
    remaining: list[str] = []
    for identifier in identifiers:
        event = events[identifier]
        stale_position = (
            maritime
            and event.subtype == "vessel_position"
            and (event.published_at is None or event.published_at < vessel_cutoff)
        )
        if (
            event.observed_at < cutoff
            or stale_position
            or (space and satellite_position_expired(event, now))
        ):
            expired.append(identifier)
        else:
            remaining.append(identifier)
    overflow = len(remaining) - budget.max_items
    if overflow <= 0:
        return expired, []
    remaining.sort(key=lambda identifier: (events[identifier].observed_at, identifier))
    return expired, remaining[:overflow]

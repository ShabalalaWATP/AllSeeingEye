"""A worker-local query index over captured immutable event references."""

from collections import defaultdict

from ase.adapters.store.query import select_events
from ase.application.ports.feeds import EventQuery
from ase.domain.events import Category, Event


class SnapshotReader:
    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.categories: dict[Category, list[Event]] = defaultdict(list)
        for event in events:
            self.categories[event.category].append(event)

    def query(self, query: EventQuery) -> list[Event]:
        candidates = (
            [event for category in query.categories for event in self.categories[category]]
            if query.categories
            else self.events
        )
        if query.country_iso:
            candidates = [e for e in candidates if e.country_iso == query.country_iso.upper()]
        return select_events(candidates, query)

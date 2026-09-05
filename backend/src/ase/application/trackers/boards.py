"""Tracker boards and detail views computed from the live store on request, never stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.trackers import ConflictDirectory
from ase.domain.errors import NotFound
from ase.domain.events import Category, Event
from ase.domain.trackers import (
    Conflict,
    ConflictCard,
    DayBucket,
    Hazard,
    HazardCard,
    conflict_card,
    hazard_card,
    hazard_cards,
    hazard_of,
    timeline,
)

WINDOW = timedelta(days=14)
POOL = 5_000
DETAIL_EVENTS = 100


@dataclass(frozen=True, slots=True)
class HazardDetail:
    card: HazardCard
    timeline: tuple[DayBucket, ...]
    events: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class ConflictDetail:
    card: ConflictCard
    timeline: tuple[DayBucket, ...]
    events: tuple[Event, ...]


class TrackerService:
    def __init__(self, store: EventStore, conflicts: ConflictDirectory, clock: Clock) -> None:
        self._store = store
        self._conflicts = conflicts
        self._clock = clock

    def disaster_board(self) -> tuple[HazardCard, ...]:
        now = self._clock.now()
        return hazard_cards(self._disasters(now), now)

    def disaster_detail(self, hazard: Hazard) -> HazardDetail:
        now = self._clock.now()
        events = [event for event in self._disasters(now) if hazard_of(event) is hazard]
        return HazardDetail(
            card=hazard_card(hazard, events, now),
            timeline=timeline(events, now),
            events=tuple(events[:DETAIL_EVENTS]),
        )

    def conflict_board(self) -> tuple[ConflictCard, ...]:
        now = self._clock.now()
        cards = [
            conflict_card(conflict, self._area_events(conflict, now), now)
            for conflict in self._conflicts.all()
        ]
        cards.sort(
            key=lambda card: (-card.activity.last_7d, -card.reporting_7d, card.conflict.name)
        )
        return tuple(cards)

    def conflict_detail(self, conflict_id: str) -> ConflictDetail:
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            raise NotFound()
        now = self._clock.now()
        events = self._area_events(conflict, now)
        fighting = [event for event in events if event.category is Category.CONFLICT]
        return ConflictDetail(
            card=conflict_card(conflict, events, now),
            timeline=timeline(fighting, now),
            events=tuple(events[:DETAIL_EVENTS]),
        )

    def _disasters(self, now: datetime) -> list[Event]:
        return self._store.query(
            EventQuery(categories=frozenset({Category.DISASTER}), since=now - WINDOW, limit=POOL)
        )

    def _area_events(self, conflict: Conflict, now: datetime) -> list[Event]:
        """Everything inside the box plus everything filed under its countries, newest first."""
        seen: dict[str, Event] = {}
        queries = [EventQuery(bbox=conflict.bbox, since=now - WINDOW, limit=POOL)]
        queries.extend(
            EventQuery(country_iso=iso, since=now - WINDOW, limit=POOL)
            for iso in conflict.countries
        )
        for query in queries:
            for event in self._store.query(query):
                seen.setdefault(event.id, event)
        return sorted(seen.values(), key=lambda event: event.published_at, reverse=True)

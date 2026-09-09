"""Tracker boards and detail views computed from the live store on request, never stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.trackers import ConflictDirectory
from ase.domain.conflict_evidence import (
    evidence_groups,
    is_conflict_context,
    is_violence,
    occurrence_time,
)
from ase.domain.conflict_relevance import is_admitted_conflict
from ase.domain.errors import NotFound
from ase.domain.events import Category, Event
from ase.domain.evidence_time import publication_order
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
        fighting = [
            group[0] for group in evidence_groups(event for event in events if is_violence(event))
        ]
        return ConflictDetail(
            card=conflict_card(conflict, events, now),
            timeline=timeline(fighting, now, time_of=occurrence_time),
            events=tuple(events[:DETAIL_EVENTS]),
        )

    def _disasters(self, now: datetime) -> list[Event]:
        return self._store.query(
            EventQuery(categories=frozenset({Category.DISASTER}), since=now - WINDOW, limit=POOL)
        )

    def _area_events(self, conflict: Conflict, now: datetime) -> list[Event]:
        """Everything inside the box plus everything filed under its countries, newest first."""
        seen: dict[str, Event] = {}
        categories = frozenset(
            {Category.CONFLICT, Category.NEWS, Category.POLITICAL, Category.HUMANITARIAN}
        )
        queries = [
            EventQuery(bbox=conflict.bbox, categories=categories, since=now - WINDOW, limit=POOL)
        ]
        queries.extend(
            EventQuery(country_iso=iso, categories=categories, since=now - WINDOW, limit=POOL)
            for iso in conflict.countries
        )
        # Monthly research releases may have no publication timestamp. Retrieve
        # them separately; occurrence dates still determine recent activity.
        queries.append(
            EventQuery(
                bbox=conflict.bbox,
                source_ids=frozenset({"ucdp_candidate", "acled_events"}),
                limit=POOL,
            )
        )
        queries.extend(
            EventQuery(
                country_iso=iso,
                source_ids=frozenset({"ucdp_candidate", "acled_events"}),
                limit=POOL,
            )
            for iso in conflict.countries
        )
        for query in queries:
            for event in self._store.query(query):
                if event.point is not None and not conflict.bbox.contains(event.point):
                    continue
                if is_admitted_conflict(event) or is_conflict_context(event):
                    seen.setdefault(event.id, event)
        return sorted(
            seen.values(),
            key=lambda event: occurrence_time(event) or publication_order(event),
            reverse=True,
        )

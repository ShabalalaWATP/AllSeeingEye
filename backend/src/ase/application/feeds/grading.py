"""Regrades a category's window of events whenever new items arrive."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.events import Event
from ase.domain.grading import SourceProfile, cutoff_for, grade_events
from ase.domain.source_ratings import unassessed_source_rating
from ase.domain.sources import SourceSpec

# Live grading is approximate context, not archival claim verification. Bound
# downstream context comparisons independently of the much larger sensor store.
MAX_POOL = 1_000


def profiles_from_specs(specs: Sequence[SourceSpec]) -> dict[str, SourceProfile]:
    return {
        spec.id: SourceProfile(
            source_id=spec.id,
            independence_key=spec.independence_key,
            name=spec.name,
            instrument=spec.instrument,
            flags=spec.flags,
            rating=spec.rating or unassessed_source_rating(),
        )
        for spec in specs
    }


class GradingService:
    """Runs the doctrine's credibility rules over the live store and writes the results back."""

    def __init__(
        self, store: EventStore, profiles: Mapping[str, SourceProfile], clock: Clock
    ) -> None:
        self._store = store
        self._profiles = profiles
        self._clock = clock

    def regrade(self, events: Sequence[Event]) -> list[Event]:
        """Regrades every category the batch touched; returns the events whose grade changed."""
        changed: list[Event] = []
        instruments = [
            event
            for event in events
            if (profile := self._profiles.get(event.source_id)) is not None and profile.instrument
        ]
        # Instrument grading is independent of narrative context. Do not leave
        # most of a large sensor batch ungraded because the topic window is full.
        for graded in grade_events(instruments, self._profiles):
            if graded.changed:
                changed.append(graded.apply())
        since = cutoff_for(self._clock.now())
        for category in sorted({event.category for event in events}, key=lambda c: c.value):
            pool = self._store.query(
                EventQuery(categories=frozenset({category}), since=since, limit=MAX_POOL)
            )
            narrative = [
                event
                for event in pool
                if (profile := self._profiles.get(event.source_id)) is None
                or not profile.instrument
            ]
            for graded in grade_events(narrative, self._profiles):
                if graded.changed:
                    changed.append(graded.apply())
        if changed:
            self._store.put(changed)
        return changed

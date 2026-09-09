"""Regrades a category's window of events whenever new items arrive."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping, Sequence
from functools import partial

from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports import Clock
from ase.application.ports.cooperative_feeds import CooperativeEventStore
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
        self._grade_slot = asyncio.Semaphore(1)

    def regrade(self, events: Sequence[Event]) -> list[Event]:
        """Regrades every category the batch touched; returns the events whose grade changed."""
        changed = [
            graded.apply()
            for batch in self._batches(events)
            for graded in grade_events(batch, self._profiles)
            if graded.changed
        ]
        if changed:
            self._store.put(changed)
        return changed

    async def regrade_cooperatively(self, events: Sequence[Event]) -> list[Event]:
        changed: list[Event] = []
        for batch in self._batches(events):
            # Pure immutable analysis can leave the API loop; store writes stay local.
            async with self._grade_slot:
                graded = await joined_thread_call(partial(grade_events, batch, self._profiles))
            for offset in range(0, len(graded), 250):
                changed.extend(
                    item.apply() for item in graded[offset : offset + 250] if item.changed
                )
                await asyncio.sleep(0)
        if isinstance(self._store, CooperativeEventStore):
            await self._store.put_grades_cooperatively(changed)
        elif changed:
            self._store.put(changed)
        return changed

    def _batches(self, events: Sequence[Event]) -> Iterator[list[Event]]:
        instruments = [
            event
            for event in events
            if (profile := self._profiles.get(event.source_id)) is not None and profile.instrument
        ]
        # Instrument grading is independent of narrative context. Do not leave
        # most of a large sensor batch ungraded because the topic window is full.
        for offset in range(0, len(instruments), 250):
            yield instruments[offset : offset + 250]
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
            if narrative:
                yield narrative

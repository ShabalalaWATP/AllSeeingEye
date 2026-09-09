"""In-memory bounded event store: windows and caps per category, plus a global memory budget."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime

from ase.adapters.store.firms_retention import firms_evictions
from ase.adapters.store.query import select_events
from ase.adapters.store.sizing import EVENT_OVERHEAD_BYTES, estimate_bytes
from ase.application.feeds.budgets import (
    DEFAULT_MEMORY_BUDGET_BYTES,
    VESSEL_POSITION_AGE,
    RetentionBudget,
    budget_for,
)
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.feeds.position_freshness import satellite_position_expired
from ase.application.ports.feeds import (
    CategoryStats,
    EventQuery,
    PruneResult,
    StoreStats,
    UpsertResult,
)
from ase.domain.errors import RateLimited
from ase.domain.events import Category, Event

__all__ = ["EVENT_OVERHEAD_BYTES", "InMemoryEventStore", "estimate_bytes"]

MAX_PRUNE_IDS = 10_000


class InMemoryEventStore:
    def __init__(
        self,
        budgets: Mapping[Category, RetentionBudget] | None = None,
        memory_budget_bytes: int = DEFAULT_MEMORY_BUDGET_BYTES,
    ) -> None:
        self._budgets = budgets or {}
        self._memory_budget = memory_budget_bytes
        self._events: dict[str, Event] = {}
        self._read_slot = asyncio.Semaphore(1)
        self._waiting_reads = 0
        self._stats_cache: StoreStats | None = None
        self._sizes: dict[str, int] = {}
        self._by_category: dict[Category, set[str]] = {}
        self._by_country: dict[str, set[str]] = {}
        self._by_source: dict[str, set[str]] = {}
        self._estimated_bytes = 0
        # Evicted between prunes to hold the memory budget; announced at the next prune.
        self._pending_expiry: set[str] = set()
        self._pending_evictions = 0
        self._pending_overflow = False

    def upsert(self, events: Iterable[Event]) -> UpsertResult:
        result = self._upsert_batch(events)
        self._capture_evictions()
        return self._retained_result(result)

    async def upsert_cooperatively(self, events: list[Event]) -> UpsertResult:
        added = updated = unchanged = 0
        changed: list[str] = []
        try:
            for offset in range(0, len(events), 250):
                result = self._upsert_batch(events[offset : offset + 250])
                added += result.added
                updated += result.updated
                unchanged += result.unchanged
                changed.extend(result.changed_ids)
                await asyncio.sleep(0)
        finally:
            # Cancellation must not leave the bounded store above its budget.
            self._capture_evictions()
        return self._retained_result(UpsertResult(added, updated, unchanged, tuple(changed)))

    def _retained_result(self, result: UpsertResult) -> UpsertResult:
        return UpsertResult(
            result.added,
            result.updated,
            result.unchanged,
            tuple(identifier for identifier in result.changed_ids if identifier in self._events),
        )

    def _upsert_batch(self, events: Iterable[Event]) -> UpsertResult:
        added = updated = unchanged = 0
        changed_ids: list[str] = []
        for event in events:
            existing = self._events.get(event.id)
            if existing is None:
                self._insert(event)
                added += 1
                changed_ids.append(event.id)
            elif (
                event.category is Category.AVIATION
                and existing.category is Category.AVIATION
                and "adsb" in event.tags
                and "adsb" in existing.tags
                and event.published_at is not None
                and existing.published_at is not None
                and event.published_at < existing.published_at
            ):
                # Overlapping regional/list polls share an ICAO identity. A slow
                # response must not move a newer transponder position backwards.
                unchanged += 1
            elif existing.content_hash == event.content_hash:
                unchanged += 1
            else:
                self._remove(event.id)
                self._insert(event)
                updated += 1
                changed_ids.append(event.id)
        return UpsertResult(
            added=added,
            updated=updated,
            unchanged=unchanged,
            changed_ids=tuple(
                identifier for identifier in changed_ids if identifier in self._events
            ),
        )

    def put(self, events: Iterable[Event]) -> None:
        for event in events:
            if event.id in self._events:
                self._remove(event.id)
            self._insert(event)
        self._capture_evictions()

    async def put_grades_cooperatively(self, events: list[Event]) -> None:
        try:
            for offset in range(0, len(events), 250):
                for event in events[offset : offset + 250]:
                    current = self._events.get(event.id)
                    if current is not None and current.content_hash == event.content_hash:
                        self._remove(event.id)
                        self._insert(event)
                await asyncio.sleep(0)
        finally:
            self._capture_evictions()

    def get(self, event_id: str) -> Event | None:
        return self._events.get(event_id)

    def query(self, query: EventQuery) -> list[Event]:
        return select_events([self._events[i] for i in self._candidates(query)], query)

    async def read_cooperatively[T](
        self, query: EventQuery, project: Callable[[list[Event]], T]
    ) -> T:
        if self._waiting_reads >= 8:
            raise RateLimited(1)
        self._waiting_reads += 1
        try:
            async with self._read_slot:
                # Capture references only after admission, never iterate live indexes in a thread.
                snapshot = [self._events[i] for i in self._candidates(query)]
                return await joined_thread_call(lambda: project(select_events(snapshot, query)))
        finally:
            self._waiting_reads -= 1

    def prune(self, now: datetime) -> PruneResult:
        expired: list[str] = []
        evicted: list[str] = []
        for category, ids in list(self._by_category.items()):
            budget = budget_for(category, self._budgets)
            cutoff = now - budget.window
            ordered = sorted(ids, key=lambda i: self._events[i].observed_at)
            for event_id in ordered:
                event = self._events[event_id]
                stale_position = (
                    event.category is Category.MARITIME
                    and event.subtype == "vessel_position"
                    and (
                        event.published_at is None or event.published_at < now - VESSEL_POSITION_AGE
                    )
                )
                if (
                    event.observed_at < cutoff
                    or stale_position
                    or satellite_position_expired(event, now)
                ):
                    expired.append(event_id)
            expired_ids = set(expired)
            remaining = [i for i in ordered if i not in expired_ids]
            overflow = len(remaining) - budget.max_items
            if overflow > 0:
                evicted.extend(remaining[:overflow])
        for event_id in expired + evicted:
            self._remove(event_id)
        self._enforce_budget(evicted)
        missing = set(expired + evicted) | self._pending_expiry
        missing.difference_update(self._events)
        result = PruneResult(
            expired=len(expired),
            evicted=len(evicted) + self._pending_evictions,
            ids=tuple(sorted(missing)[:MAX_PRUNE_IDS]),
            resync_required=self._pending_overflow or len(missing) > MAX_PRUNE_IDS,
        )
        self._pending_expiry.clear()
        self._pending_evictions = 0
        self._pending_overflow = False
        return result

    def stats(self) -> StoreStats:
        if self._stats_cache is not None:
            return self._stats_cache
        per_category = []
        for category, ids in sorted(self._by_category.items(), key=lambda kv: kv[0].value):
            if not ids:
                continue
            times = [self._events[i].observed_at for i in ids]
            per_category.append(CategoryStats(category, len(ids), min(times), max(times)))
        self._stats_cache = StoreStats(
            total=len(self._events),
            estimated_bytes=self._estimated_bytes,
            budget_bytes=self._memory_budget,
            per_category=tuple(per_category),
        )

        return self._stats_cache

    def _candidates(self, query: EventQuery) -> Iterable[str]:
        if query.source_ids:
            source_ids: set[str] = set()
            for source_id in query.source_ids:
                source_ids.update(self._by_source.get(source_id, ()))
            return [
                i
                for i in source_ids
                if (not query.categories or self._events[i].category in query.categories)
                and (
                    not query.country_iso
                    or i in self._by_country.get(query.country_iso.upper(), ())
                )
            ]
        if query.country_iso:
            ids = self._by_country.get(query.country_iso.upper(), set())
            if query.categories:
                return [i for i in ids if self._events[i].category in query.categories]
            return list(ids)
        if query.categories:
            result: list[str] = []
            for category in query.categories:
                result.extend(self._by_category.get(category, ()))
            return result
        return list(self._events)

    def _enforce_budget(self, evicted: list[str]) -> None:
        """Drops the oldest observed events until the memory estimate fits the budget."""
        for identifier in firms_evictions(self._events, self._by_source):
            self._remove(identifier)
            evicted.append(identifier)
        if self._estimated_bytes <= self._memory_budget:
            return
        for event_id in sorted(self._events, key=lambda i: self._events[i].observed_at):
            if self._estimated_bytes <= self._memory_budget:
                break
            self._remove(event_id)
            evicted.append(event_id)

    def _capture_evictions(self) -> None:
        evicted: list[str] = []
        self._enforce_budget(evicted)
        self._pending_evictions += len(evicted)
        for event_id in evicted:
            if event_id in self._pending_expiry:
                continue
            if len(self._pending_expiry) < MAX_PRUNE_IDS:
                self._pending_expiry.add(event_id)
            else:
                self._pending_overflow = True

    def _insert(self, event: Event) -> None:
        self._stats_cache = None
        self._pending_expiry.discard(event.id)
        self._events[event.id] = event
        size = estimate_bytes(event)
        self._sizes[event.id] = size
        self._estimated_bytes += size
        self._by_category.setdefault(event.category, set()).add(event.id)
        self._by_source.setdefault(event.source_id, set()).add(event.id)
        if event.country_iso:
            self._by_country.setdefault(event.country_iso.upper(), set()).add(event.id)

    def _remove(self, event_id: str) -> None:
        event = self._events.pop(event_id, None)
        if event is None:
            return
        self._stats_cache = None
        self._estimated_bytes -= self._sizes.pop(event_id, 0)
        self._by_category.get(event.category, set()).discard(event_id)
        self._by_source.get(event.source_id, set()).discard(event_id)
        if event.country_iso:
            self._by_country.get(event.country_iso.upper(), set()).discard(event_id)

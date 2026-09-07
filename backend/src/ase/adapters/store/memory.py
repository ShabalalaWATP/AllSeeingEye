"""In-memory bounded event store: windows and caps per category, plus a global memory budget."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from ase.application.feeds.budgets import (
    DEFAULT_MEMORY_BUDGET_BYTES,
    RetentionBudget,
    budget_for,
)
from ase.application.ports.feeds import (
    CategoryStats,
    EventQuery,
    PruneResult,
    StoreStats,
    UpsertResult,
)
from ase.domain.events import Category, Event

MAX_PRUNE_IDS = 10_000
EVENT_OVERHEAD_BYTES = 240


def estimate_bytes(event: Event) -> int:
    size = EVENT_OVERHEAD_BYTES + len(event.title) + len(event.id)
    size += len(event.summary or "") + len(event.url or "") + len(event.title_en or "")
    size += sum(len(key) + len(str(value)) for key, value in event.attributes.items())
    size += sum(len(tag) for tag in event.tags)
    if event.geometry is not None:
        geometry = event.geometry
        size += len(geometry.source_geometry.encode("utf-8"))
        size += (
            sum(
                len(value.encode("utf-8"))
                for value in (
                    geometry.precision,
                    geometry.method,
                    geometry.source_id,
                    geometry.attribution,
                )
            )
            + 256
        )
    if event.observation is not None:
        observation = event.observation
        size += (
            sum(
                len(value.encode("utf-8"))
                for value in (
                    observation.collection_id,
                    observation.item_id,
                    observation.limitations,
                )
            )
            + 256
        )
    return size


class InMemoryEventStore:
    def __init__(
        self,
        budgets: Mapping[Category, RetentionBudget] | None = None,
        memory_budget_bytes: int = DEFAULT_MEMORY_BUDGET_BYTES,
    ) -> None:
        self._budgets = budgets or {}
        self._memory_budget = memory_budget_bytes
        self._events: dict[str, Event] = {}
        self._sizes: dict[str, int] = {}
        self._by_category: dict[Category, set[str]] = {}
        self._by_country: dict[str, set[str]] = {}
        self._estimated_bytes = 0
        # Evicted between prunes to hold the memory budget; announced at the next prune.
        self._pending_expiry: list[str] = []

    def upsert(self, events: Iterable[Event]) -> UpsertResult:
        added = updated = unchanged = 0
        changed_ids: list[str] = []
        for event in events:
            existing = self._events.get(event.id)
            if existing is None:
                self._insert(event)
                added += 1
                changed_ids.append(event.id)
            elif existing.content_hash == event.content_hash:
                unchanged += 1
            else:
                self._remove(event.id)
                self._insert(event)
                updated += 1
                changed_ids.append(event.id)
        self._enforce_budget(self._pending_expiry)
        return UpsertResult(
            added=added, updated=updated, unchanged=unchanged, changed_ids=tuple(changed_ids)
        )

    def put(self, events: Iterable[Event]) -> None:
        for event in events:
            if event.id in self._events:
                self._remove(event.id)
            self._insert(event)
        self._enforce_budget(self._pending_expiry)

    def get(self, event_id: str) -> Event | None:
        return self._events.get(event_id)

    def query(self, query: EventQuery) -> list[Event]:
        candidates = self._candidates(query)
        matched: list[Event] = []
        for event_id in candidates:
            event = self._events[event_id]
            if query.source_ids and event.source_id not in query.source_ids:
                continue
            if query.since is not None and event.published_at < query.since:
                continue
            if query.bbox is not None and (
                event.point is None or not query.bbox.contains(event.point)
            ):
                continue
            matched.append(event)
        matched.sort(key=lambda e: e.published_at, reverse=True)
        return matched[: max(1, query.limit)]

    def prune(self, now: datetime) -> PruneResult:
        expired: list[str] = []
        evicted: list[str] = []
        for category, ids in list(self._by_category.items()):
            budget = budget_for(category, self._budgets)
            cutoff = now - budget.window
            ordered = sorted(ids, key=lambda i: self._events[i].observed_at)
            for event_id in ordered:
                if self._events[event_id].observed_at < cutoff:
                    expired.append(event_id)
            expired_ids = set(expired)
            remaining = [i for i in ordered if i not in expired_ids]
            overflow = len(remaining) - budget.max_items
            if overflow > 0:
                evicted.extend(remaining[:overflow])
        for event_id in expired + evicted:
            self._remove(event_id)
        evicted.extend(self._pending_expiry)
        self._pending_expiry = []
        self._enforce_budget(evicted)
        pruned_ids = tuple((expired + evicted)[:MAX_PRUNE_IDS])
        return PruneResult(expired=len(expired), evicted=len(evicted), ids=pruned_ids)

    def stats(self) -> StoreStats:
        per_category = []
        for category, ids in sorted(self._by_category.items(), key=lambda kv: kv[0].value):
            if not ids:
                continue
            times = [self._events[i].observed_at for i in ids]
            per_category.append(CategoryStats(category, len(ids), min(times), max(times)))
        return StoreStats(
            total=len(self._events),
            estimated_bytes=self._estimated_bytes,
            budget_bytes=self._memory_budget,
            per_category=tuple(per_category),
        )

    def _candidates(self, query: EventQuery) -> Iterable[str]:
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
        if self._estimated_bytes <= self._memory_budget:
            return
        for event_id in sorted(self._events, key=lambda i: self._events[i].observed_at):
            if self._estimated_bytes <= self._memory_budget:
                break
            self._remove(event_id)
            evicted.append(event_id)

    def _insert(self, event: Event) -> None:
        self._events[event.id] = event
        size = estimate_bytes(event)
        self._sizes[event.id] = size
        self._estimated_bytes += size
        self._by_category.setdefault(event.category, set()).add(event.id)
        if event.country_iso:
            self._by_country.setdefault(event.country_iso.upper(), set()).add(event.id)

    def _remove(self, event_id: str) -> None:
        event = self._events.pop(event_id, None)
        if event is None:
            return
        self._estimated_bytes -= self._sizes.pop(event_id, 0)
        self._by_category.get(event.category, set()).discard(event_id)
        if event.country_iso:
            self._by_country.get(event.country_iso.upper(), set()).discard(event_id)

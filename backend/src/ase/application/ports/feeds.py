"""Ports for the fusion core: connectors, the bounded live store and the event bus."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from ase.domain.events import BoundingBox, Category, Event
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.sources import SourceSpec


class FeedConnector(Protocol):
    @property
    def spec(self) -> SourceSpec: ...

    async def fetch(self) -> list[Event]:
        """Fetch the source and return normalised events. Raise on failure."""
        ...


@dataclass(frozen=True, slots=True)
class EventQuery:
    categories: frozenset[Category] = frozenset()
    bbox: BoundingBox | None = None
    country_iso: str | None = None
    since: datetime | None = None
    source_ids: frozenset[str] = frozenset()
    limit: int = 500
    until: datetime | None = None
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION


@dataclass(frozen=True, slots=True)
class UpsertResult:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    changed_ids: tuple[str, ...] = ()

    @property
    def changed(self) -> int:
        return self.added + self.updated


@dataclass(frozen=True, slots=True)
class PruneResult:
    expired: int = 0
    evicted: int = 0
    ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CategoryStats:
    category: Category
    count: int
    oldest: datetime | None
    newest: datetime | None


@dataclass(frozen=True, slots=True)
class StoreStats:
    total: int
    estimated_bytes: int
    budget_bytes: int
    per_category: tuple[CategoryStats, ...] = ()


class EventStore(Protocol):
    def upsert(self, events: Iterable[Event]) -> UpsertResult: ...
    def put(self, events: Iterable[Event]) -> None:
        """Replace events regardless of content hash (used when grades change)."""
        ...

    def get(self, event_id: str) -> Event | None: ...
    def query(self, query: EventQuery) -> list[Event]: ...
    def prune(self, now: datetime) -> PruneResult: ...
    def stats(self) -> StoreStats: ...


@dataclass(frozen=True, slots=True)
class BusMessage:
    kind: str
    payload: Mapping[str, object] = field(default_factory=dict)


class Subscription(Protocol):
    def __aiter__(self) -> AsyncIterator[BusMessage]: ...
    def close(self) -> None: ...


class Grader(Protocol):
    def regrade(self, events: Sequence[Event]) -> list[Event]:
        """Regrade the categories the batch touched; return the events whose grade changed."""
        ...


class EventBus(Protocol):
    async def publish(self, message: BusMessage) -> None: ...
    def subscribe(self) -> Subscription: ...

"""Bounded contracts for independent selected-subscription acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from ase.domain.schedules import Schedule
from ase.domain.selected_subscription_index import SelectedMetadata


@dataclass(frozen=True, slots=True)
class IndexedSourcePolicy:
    """Reviewed metadata permission for one fixed public source and capability."""

    source_id: str
    capability_id: str
    policy_id: str
    retention_days: int
    minimum_interval: timedelta
    overlap: timedelta
    cache_history: timedelta
    max_cache_age: timedelta

    def __post_init__(self) -> None:
        if (
            not self.source_id
            or not self.capability_id
            or not self.policy_id
            or not 1 <= self.retention_days <= 400
            or not timedelta(hours=1) <= self.minimum_interval <= timedelta(days=30)
            or not timedelta(minutes=1) <= self.overlap <= timedelta(days=7)
            or not timedelta(minutes=1) <= self.cache_history <= timedelta(days=7)
            or not timedelta(minutes=1) <= self.max_cache_age <= timedelta(days=2)
        ):
            raise ValueError("Invalid reviewed selected-index source policy")


@dataclass(frozen=True, slots=True)
class IndexCursor:
    revision: int
    cursor_value: str | None
    watermark_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class IndexedPage:
    records: tuple[SelectedMetadata, ...]
    next_after: str | None
    truncated: bool = False


class CacheUnavailable(Exception):
    """The fixed public feed cache cannot establish a current page."""


class IndexedPageSource(Protocol):
    async def fetch_page(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        *,
        since: datetime,
        until: datetime,
        after: str | None,
        limit: int,
    ) -> IndexedPage: ...


class SelectedIndexAcquisitionStore(Protocol):
    async def active_batch(self, after: UUID | None, limit: int) -> tuple[Schedule, ...]: ...

    async def current(self, subscription_id: UUID) -> Schedule | None: ...

    async def cursor(self, schedule: Schedule, source_id: str) -> IndexCursor | None: ...

    async def persist(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        *,
        expected_revision: int,
        page_key: str,
        page: IndexedPage,
        cursor_value: str | None,
        watermark_at: datetime,
        now: datetime,
    ) -> bool: ...

    async def record_gap(
        self,
        schedule: Schedule,
        source_id: str,
        *,
        reason: str,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> None: ...

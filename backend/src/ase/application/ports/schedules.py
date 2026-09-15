"""Ports for scheduled products."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.schedules import Schedule, ScheduleErrorCode, ScheduleRunResult


class ScheduleRepository(Protocol):
    async def add(self, schedule: Schedule) -> None: ...
    async def get(self, schedule_id: UUID) -> Schedule | None: ...
    async def list_all(self, visibility: Visibility) -> list[Schedule]: ...
    async def save(self, schedule: Schedule) -> None: ...
    async def archive(self, schedule: Schedule, archived_at: datetime) -> bool: ...


class ScheduleStore(Protocol):
    """What the background runner needs; each call runs in its own session."""

    async def due(self, now: datetime) -> list[Schedule]: ...
    async def can_run(self, schedule: Schedule) -> bool: ...
    async def mark_run(
        self,
        schedule_id: UUID,
        *,
        ran_at: datetime,
        next_run_at: datetime,
        result: ScheduleRunResult | None,
        error_code: ScheduleErrorCode | None,
        expected: Schedule,
    ) -> None: ...

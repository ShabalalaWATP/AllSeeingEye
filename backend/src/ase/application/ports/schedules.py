"""Ports for scheduled products."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.schedules import Schedule


class ScheduleRepository(Protocol):
    async def add(self, schedule: Schedule) -> None: ...
    async def get(self, schedule_id: UUID) -> Schedule | None: ...
    async def list_all(self) -> list[Schedule]: ...
    async def save(self, schedule: Schedule) -> None: ...
    async def delete(self, schedule_id: UUID) -> None: ...


class ScheduleStore(Protocol):
    """What the background runner needs; each call runs in its own session."""

    async def due(self, now: datetime) -> list[Schedule]: ...
    async def mark_run(
        self,
        schedule_id: UUID,
        *,
        ran_at: datetime,
        next_run_at: datetime,
        report_id: UUID | None,
        error: str | None,
    ) -> None: ...

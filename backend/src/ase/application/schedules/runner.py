"""The runner: every minute, produce whatever schedules have fallen due and book the next run."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from uuid import UUID

from ase.application.ports import Clock
from ase.application.ports.schedules import ScheduleStore
from ase.domain.schedules import Schedule, next_run_after

log = logging.getLogger(__name__)

INTERVAL = timedelta(seconds=60)
Producer = Callable[[Schedule], Awaitable[UUID]]
SleepFn = Callable[[float], Awaitable[None]]


class ScheduleRunner:
    def __init__(
        self,
        schedules: ScheduleStore,
        producer: Producer,
        clock: Clock,
        *,
        interval: timedelta = INTERVAL,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._schedules = schedules
        self._producer = producer
        self._clock = clock
        self._interval = interval
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def run_once(self) -> list[Schedule]:
        now = self._clock.now()
        ran: list[Schedule] = []
        for schedule in await self._schedules.due(now):
            if not await self._schedules.can_run(schedule):
                continue
            report_id: UUID | None = None
            error: str | None = None
            try:
                report_id = await self._producer(schedule)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"[:300]
                log.warning("schedule_failed", extra={"schedule": schedule.name, "error": error})
            await self._schedules.mark_run(
                schedule.id,
                ran_at=now,
                next_run_at=next_run_after(
                    now, schedule.hour_utc, schedule.cadence, schedule.weekday
                ),
                report_id=report_id,
                error=error,
                expected=schedule,
            )
            ran.append(schedule)
        return ran

    async def start(self) -> None:
        if self._task is None:
            self._stopping.clear()
            self._task = asyncio.create_task(self._run(), name="schedule-runner")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.run_once()
            except Exception:
                log.exception("schedule_cycle_failed")
            await self._sleep(self._interval.total_seconds())

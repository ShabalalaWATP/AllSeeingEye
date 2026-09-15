"""Poll due subscriptions and enqueue existing durable report jobs."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

log = logging.getLogger(__name__)

INTERVAL = timedelta(seconds=60)
SleepFn = Callable[[float], Awaitable[None]]
EnqueueTick = Callable[[], Awaitable[int]]
AcquisitionTick = Callable[[], Awaitable[int]]


@dataclass(frozen=True, slots=True)
class DueCursor:
    """The last fair-sort key seen in one process's bounded due polling."""

    owner_rank: int
    owner_id: UUID
    item_id: UUID


class ScheduleRunner:
    """Poll due editions and admit jobs; paid work belongs to report workers."""

    def __init__(
        self,
        enqueue_tick: EnqueueTick,
        *,
        acquisition_tick: AcquisitionTick | None = None,
        interval: timedelta = INTERVAL,
        acquisition_interval: timedelta = INTERVAL,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._enqueue_tick = enqueue_tick
        self._acquisition_tick = acquisition_tick
        self._interval = interval
        self._acquisition_interval = acquisition_interval
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None
        self._acquisition_task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def run_once(self) -> int:
        return await self._enqueue_tick()

    async def acquire_once(self) -> int:
        return await self._acquisition_tick() if self._acquisition_tick is not None else 0

    async def start(self) -> None:
        if self._task is None:
            self._stopping.clear()
            self._task = asyncio.create_task(self._run(), name="subscription-enqueue")
            if self._acquisition_tick is not None:
                self._acquisition_task = asyncio.create_task(
                    self._run_acquisition(), name="subscription-selected-index"
                )

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._acquisition_task is not None:
            self._acquisition_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._acquisition_task
            self._acquisition_task = None

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.run_once()
            except Exception:
                log.warning("subscription_enqueue_cycle_failed")
            await self._sleep(self._interval.total_seconds())

    async def _run_acquisition(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.acquire_once()
            except Exception:
                log.warning("subscription_selected_index_cycle_failed")
            await self._sleep(self._acquisition_interval.total_seconds())

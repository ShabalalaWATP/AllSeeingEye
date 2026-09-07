"""Fair bounded polling survives transient cycles and propagates cancellation."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

log = logging.getLogger(__name__)
Due = Callable[[int, UUID | None], Awaitable[list[UUID]]]
Observe = Callable[[UUID], Awaitable[bool]]
Sleep = Callable[[float], Awaitable[None]]


class AnnotationMonitorWorker:
    def __init__(self, due: Due, observe: Observe, *, sleep: Sleep = asyncio.sleep) -> None:
        self.due, self.observe, self.sleep = due, observe, sleep
        self.cursor: UUID | None = None

    async def run_once(self) -> int:
        ids = await self.due(20, self.cursor)
        if not ids:
            self.cursor = None
            return 0
        count = 0
        for key in ids:
            try:
                count += int(await self.observe(key))
            except Exception:
                log.warning("annotation_monitor.observation_failed")
            self.cursor = key
        if len(ids) < 20:
            self.cursor = None
        return count

    async def run(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:
                # No database/source content is included in shared logs.
                log.warning("annotation_monitor.cycle_failed")
            await self.sleep(5)

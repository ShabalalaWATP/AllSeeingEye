"""One active FIRMS parser per event loop, retaining ownership until its worker ends."""

import asyncio
from collections.abc import Callable
from datetime import datetime
from weakref import WeakKeyDictionary

from ase.adapters.feeds.firms_sensors import FirmsSensor
from ase.domain.events import Event

_SLOTS: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = WeakKeyDictionary()


async def parse_off_loop(
    parser: Callable[[bytes, datetime, FirmsSensor], list[Event]],
    payload: bytes,
    now: datetime,
    sensor: FirmsSensor,
) -> list[Event]:
    loop = asyncio.get_running_loop()
    slots = _SLOTS.setdefault(loop, asyncio.Semaphore(1))
    async with slots:
        task = asyncio.create_task(asyncio.to_thread(parser, payload, now, sensor))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # A thread cannot be cancelled. Join it before releasing capacity so
            # request cancellation cannot accumulate overlapping parser heaps.
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not task.cancelled():
                task.exception()
            raise

"""Queueing for a shared upstream host does not spend a poll's fetch budget.

The poller bounds each fetch with a deadline and one of a few process-wide slots.
Connectors that share a paced host (dozens of Telegram channels behind one t.me
gap) can queue for minutes after a restart. That queueing is politeness, not
upstream slowness: while a request waits for its host turn, the poll hands its
fetch slot back and its deadlines stop counting, then both resume for the request.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from types import TracebackType


class _Frame:
    """The slot and deadlines one fetch holds; shared by tasks the fetch spawns."""

    def __init__(self, slots: asyncio.Semaphore | None) -> None:
        self.slots = slots
        self.held = False
        self.deadlines: list[asyncio.Timeout] = []
        self.remaining: dict[int, float] = {}

    def suspend(self) -> None:
        if self.slots is not None and self.held:
            self.held = False
            self.slots.release()
        now = asyncio.get_running_loop().time()
        for deadline in self.deadlines:
            when = deadline.when()
            if when is None or deadline.expired() or id(deadline) in self.remaining:
                continue
            self.remaining[id(deadline)] = max(0.0, when - now)
            deadline.reschedule(None)

    async def resume(self) -> None:
        if self.slots is not None and not self.held:
            await self.slots.acquire()
            self.held = True
        now = asyncio.get_running_loop().time()
        for deadline in self.deadlines:
            remaining = self.remaining.pop(id(deadline), None)
            if remaining is not None and not deadline.expired():
                deadline.reschedule(now + remaining)


_ACTIVE: ContextVar[_Frame | None] = ContextVar("ase_fetch_budget", default=None)


@asynccontextmanager
async def fetch_budget(slots: asyncio.Semaphore, seconds: float) -> AsyncIterator[None]:
    """Hold one fetch slot under a deadline; both pause while queued for a paced host."""
    frame = _Frame(slots)
    await slots.acquire()
    frame.held = True
    token = _ACTIVE.set(frame)
    try:
        async with asyncio.timeout(seconds) as deadline:
            frame.deadlines.append(deadline)
            yield
    finally:
        _ACTIVE.reset(token)
        if frame.held:
            frame.held = False
            slots.release()


@asynccontextmanager
async def pausable_timeout(seconds: float) -> AsyncIterator[None]:
    """`asyncio.timeout` whose clock stops while the request queues for its host."""
    frame = _ACTIVE.get()
    token = None
    if frame is None:
        frame = _Frame(None)
        token = _ACTIVE.set(frame)
    try:
        async with asyncio.timeout(seconds) as deadline:
            frame.deadlines.append(deadline)
            try:
                yield
            finally:
                frame.deadlines.remove(deadline)
                frame.remaining.pop(id(deadline), None)
    finally:
        if token is not None:
            _ACTIVE.reset(token)


class UpstreamQueue:
    """Entered while waiting for a host turn; `resume` reclaims the budget before sending.

    Resuming inside the pacer's host lock keeps request starts in pacing order even
    when every fetch slot is busy. Exit resumes too unless the task is being cancelled.
    """

    def __init__(self) -> None:
        self._frame = _ACTIVE.get()

    async def __aenter__(self) -> UpstreamQueue:
        if self._frame is not None:
            self._frame.suspend()
        return self

    async def resume(self) -> None:
        if self._frame is not None:
            await self._frame.resume()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None or issubclass(exc_type, Exception):
            await self.resume()

"""Runs every connector on its own interval with timeouts, backoff and health tracking."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Sequence
from datetime import timedelta

from ase.application.feeds.cadence import first_poll_delay, next_poll_delay
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.poll_outcome import PollOutcome
from ase.application.feeds.poller import FeedPoller
from ase.application.ports import Clock
from ase.application.ports.feed_diagnostics import DiagnosticFeedConnector
from ase.application.ports.feeds import BusMessage, EventBus, EventStore, FeedConnector, Grader
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.errors import NotFound

SleepFn = Callable[[float], Awaitable[None]]
__all__ = ["FeedScheduler", "PollOutcome"]


class FeedScheduler(FeedPoller):
    """Owns when each source polls; FeedPoller owns what a single poll does."""

    def __init__(
        self,
        connectors: Sequence[FeedConnector],
        pipeline: Pipeline,
        store: EventStore,
        bus: EventBus,
        health: HealthRegistry,
        clock: Clock,
        *,
        fetch_timeout: timedelta | None = None,
        prune_interval: timedelta = timedelta(seconds=60),
        jitter: float = 0.1,
        sleep: SleepFn = asyncio.sleep,
        grader: Grader | None = None,
        admission: SourceAdmission | None = None,
        processing_timeout: timedelta = timedelta(seconds=60),
        fetch_concurrency: int = 16,
        first_poll_spread: timedelta = timedelta(seconds=60),
    ) -> None:
        super().__init__(
            pipeline,
            store,
            bus,
            health,
            clock,
            fetch_timeout=fetch_timeout,
            grader=grader,
            admission=admission,
            processing_timeout=processing_timeout,
            fetch_concurrency=fetch_concurrency,
        )
        self._connectors = {connector.spec.id: connector for connector in connectors}
        self._prune_interval = prune_interval
        self._jitter = jitter
        self._sleep = sleep
        self._first_poll_spread = first_poll_spread
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._retiring_tasks: set[asyncio.Task[None]] = set()
        self._prune_task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._restarting: set[str] = set()

    @property
    def connectors(self) -> list[FeedConnector]:
        return list(self._connectors.values())

    @property
    def running(self) -> bool:
        return self._prune_task is not None

    async def start(self) -> None:
        self._stopping.clear()
        for source_id, connector in self._connectors.items():
            self._tasks[source_id] = asyncio.create_task(self._run_connector(connector))
        self._prune_task = asyncio.create_task(self._prune_loop())

    async def stop(self) -> None:
        self._stopping.set()
        tasks = [*self._tasks.values(), *self._retiring_tasks]
        if self._prune_task is not None:
            tasks.append(self._prune_task)
        for task in tasks:
            task.cancel()
        for task in tasks:
            # Shutdown must never raise, whatever a connector was doing.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._tasks.clear()
        self._retiring_tasks.clear()
        self._restarting.clear()
        self._prune_task = None

    def resume(self, source_id: str) -> None:
        """Re-enable a source an administrator has reset after the breaker disabled it."""
        connector = self._connectors.get(source_id)
        if connector is None:
            raise NotFound()
        entry = self._health.reset(source_id)
        deadline = self._retry_not_before.get(source_id)
        if deadline is not None and deadline > self._clock.now():
            entry.next_poll_at = deadline
        task = self._tasks.get(source_id)
        if isinstance(connector, DiagnosticFeedConnector):
            connector.request_retry()
        if self.running and source_id not in self._restarting:
            if task is not None and not task.done():
                task.cancel()
                self._retiring_tasks.add(task)
                task.add_done_callback(self._retiring_tasks.discard)
            self._restarting.add(source_id)
            self._tasks[source_id] = asyncio.create_task(self._restart(connector, task))

    async def _restart(self, connector: FeedConnector, previous: asyncio.Task[None] | None) -> None:
        # Await cancellation cleanup before another request can use the same connector.
        try:
            if previous is not None:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await previous
        finally:
            self._restarting.discard(connector.spec.id)
        if not self._stopping.is_set():
            # A deliberate reset polls at once; only start-up polls are spread out.
            await self._run_connector(connector, first_delay=0.0)

    async def _run_connector(
        self, connector: FeedConnector, *, first_delay: float | None = None
    ) -> None:
        spec = connector.spec
        # Spread the first polls so a restart does not hit every upstream at once.
        if first_delay is None:
            first_delay = first_poll_delay(spec, self._first_poll_spread)
        await self._sleep(first_delay)
        while not self._stopping.is_set():
            await self.poll_once(connector)
            entry = self._health.get(spec.id)
            if entry.status is SourceStatus.DISABLED:
                return
            await self._sleep(
                next_poll_delay(entry, spec.poll_interval, self._clock.now(), self._jitter)
            )

    async def _prune_loop(self) -> None:
        while not self._stopping.is_set():
            await self._sleep(self._prune_interval.total_seconds())
            result = self._store.prune(self._clock.now())
            if result.resync_required:
                await self._bus.publish(BusMessage("event.resync", {"reason": "expiry_overflow"}))
            elif result.ids:
                await self._bus.publish(
                    BusMessage("event.expire", {"ids": result.ids, "count": len(result.ids)})
                )

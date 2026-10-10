"""Runs every connector on its own interval with timeouts, backoff and health tracking."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Sequence
from contextvars import copy_context
from datetime import timedelta

from ase.application.feeds.cadence import (
    MIN_DELAY_SECONDS,
    first_poll_delay,
    next_poll_delay,
)
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.poll_outcome import PollOutcome
from ase.application.feeds.poller import FeedPoller
from ase.application.ports import Clock
from ase.application.ports.cooperative_feeds import WithdrawableEventStore
from ase.application.ports.feed_diagnostics import DiagnosticFeedConnector
from ase.application.ports.feeds import EventBus, EventStore, FeedConnector, Grader
from ase.application.ports.source_controls import SourceAdmission
from ase.application.worker_progress import register_worker, run_cycle, worker_heartbeats
from ase.domain.errors import NotFound
from ase.domain.source_controls import source_control_keys
from ase.domain.source_licences import LICENCE_UNAVAILABLE, SourceLicencePolicy

SleepFn = Callable[[float], Awaitable[None]]
__all__ = ["FeedScheduler", "PollOutcome"]
log = logging.getLogger(__name__)


class FeedScheduler:
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
        licences: SourceLicencePolicy | None = None,
    ) -> None:
        self.poller = FeedPoller(
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
        self._clock = clock
        self._licences = licences or SourceLicencePolicy(())
        self._health = health
        self._store = store
        self._connectors = {connector.spec.id: connector for connector in connectors}
        self._prune_interval = prune_interval
        self._jitter = jitter
        self._sleep = sleep
        self._first_poll_spread = first_poll_spread
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._retiring_tasks: set[asyncio.Task[None]] = set()
        self._prune_task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._worker_context = copy_context()
        self._restarting: set[str] = set()

    async def poll_once(self, connector: FeedConnector) -> PollOutcome:
        """Poll a source directly through the same bounded poller used by scheduled work."""
        return await self.poller.poll_once(connector)

    @property
    def connectors(self) -> list[FeedConnector]:
        return list(self._connectors.values())

    @property
    def running(self) -> bool:
        return self._prune_task is not None

    async def start(self) -> None:
        self._worker_context = copy_context()
        self._stopping.clear()
        for source_id, connector in self._connectors.items():
            if not self._licences.allowed(source_id):
                self._health.licence_disabled(source_id, LICENCE_UNAVAILABLE)
                continue
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
        """Resume a source an administrator has reset, without waiting for its cool-down."""
        connector = self._connectors.get(source_id)
        if connector is None:
            raise NotFound()
        self._licences.require(source_id)
        self.poller.reset(source_id)
        task = self._tasks.get(source_id)
        if isinstance(connector, DiagnosticFeedConnector):
            connector.request_retry()
        if self.running and source_id not in self._restarting:
            if task is not None and not task.done():
                task.cancel()
                self._retiring_tasks.add(task)
                task.add_done_callback(self._retiring_tasks.discard)
            self._restarting.add(source_id)
            self._tasks[source_id] = asyncio.create_task(
                self._restart(connector, task), context=self._worker_context.copy()
            )

    async def withdraw(self, source_id: str) -> int:
        """Remove a just-disabled source's live events, including child sources it gates.

        The caller holds the admission guard, so no poll of these sources can publish
        in between; the prune announces the removals to streams straight away.
        """
        if not isinstance(self._store, WithdrawableEventStore):
            return 0
        affected = [
            connector_id
            for connector_id in self._connectors
            if source_id in source_control_keys(connector_id)
        ]
        withdrawn = self._store.withdraw_sources(affected)
        if withdrawn:
            await self.poller.prune()
        return withdrawn

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
        name = f"feed:{spec.id}"
        allowance = max(spec.poll_interval.total_seconds(), first_delay, 180.0)
        register_worker(name, allowance)
        await self._sleep(first_delay)
        while not self._stopping.is_set():
            # An unexpected failure costs one cycle, never the source's loop.
            delay = max(MIN_DELAY_SECONDS, spec.poll_interval.total_seconds())
            try:
                await run_cycle(name, allowance, lambda: self.poll_once(connector))
                # A source the breaker paused sleeps until its cool-down probe, not forever.
                entry = self.poller.health_for(spec.id)
                delay = next_poll_delay(entry, spec.poll_interval, self._clock.now(), self._jitter)
                allowance = max(delay, 180.0)
                if registry := worker_heartbeats.get():
                    registry.completed(name, allowance)
            except Exception as exc:
                # The class name only: messages can carry feed URLs and their credentials.
                log.error(
                    "feed_cycle_failed", extra={"source_id": spec.id, "error": type(exc).__name__}
                )
            await self._sleep(delay)

    async def _prune_loop(self) -> None:
        register_worker("scheduler", self._prune_interval.total_seconds())
        interval = self._prune_interval.total_seconds()
        while not self._stopping.is_set():
            await self._sleep(interval)
            try:
                # Records completion, or a failed cycle, against the scheduler heartbeat.
                await run_cycle("scheduler", interval, self.poller.prune)
            except Exception as exc:
                log.error("feed_prune_failed", extra={"error": type(exc).__name__})

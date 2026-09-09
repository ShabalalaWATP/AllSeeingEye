"""Runs every connector on its own interval with timeouts, backoff and health tracking."""

from __future__ import annotations

import asyncio
import contextlib
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Pipeline
from ase.application.ports import Clock
from ase.application.ports.feed_diagnostics import DiagnosticFeedConnector, FeedDeferred
from ase.application.ports.feed_release import FeedUnavailable, GuardedFeedConnector
from ase.application.ports.feeds import BusMessage, EventBus, EventStore, FeedConnector, Grader
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.errors import NotFound
from ase.domain.events import Event

SleepFn = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PollOutcome:
    source_id: str
    ok: bool
    fetched: int = 0
    changed: int = 0
    error: str | None = None


class FeedScheduler:
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
    ) -> None:
        self._connectors = {connector.spec.id: connector for connector in connectors}
        self._pipeline = pipeline
        self._store = store
        self._bus = bus
        self._health = health
        self._clock = clock
        self._fetch_timeout = fetch_timeout
        self._prune_interval = prune_interval
        self._jitter = jitter
        self._sleep = sleep
        self._grader = grader
        self._admission = admission
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._retiring_tasks: set[asyncio.Task[None]] = set()
        self._prune_task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

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
        self._prune_task = None

    def resume(self, source_id: str) -> None:
        """Re-enable a source an administrator has reset after the breaker disabled it."""
        connector = self._connectors.get(source_id)
        if connector is None:
            raise NotFound()
        self._health.reset(source_id)
        task = self._tasks.get(source_id)
        if isinstance(connector, DiagnosticFeedConnector):
            connector.request_retry()
            if task is not None:
                task.cancel()
                self._retiring_tasks.add(task)
                task.add_done_callback(self._retiring_tasks.discard)
                task = None
        if self.running and (task is None or task.done()):
            self._tasks[source_id] = asyncio.create_task(self._run_connector(connector))

    async def poll_once(self, connector: FeedConnector) -> PollOutcome:
        source_id = connector.spec.id
        started = self._clock.now()
        generation: int | None = None
        try:
            if self._admission is not None and not await self._admission.enabled(source_id):
                raise FeedUnavailable("Disabled by administrator.")
            # World FIRMS responses have exceeded 60s in measured collection.
            # Explicit caller timeouts still override these fixed-source defaults.
            timeout = self._fetch_timeout
            if timeout is None:
                seconds = 120 if source_id in {"firms_viirs_noaa20", "firms_viirs_noaa21"} else 60
                timeout = timedelta(seconds=seconds)
            async with asyncio.timeout(timeout.total_seconds()):
                if isinstance(connector, GuardedFeedConnector):
                    generation = await connector.current_generation()
                batch = (
                    await connector.fetch_batch()
                    if isinstance(connector, GuardedFeedConnector)
                    else None
                )
                raw = batch.events if batch is not None else await connector.fetch()
            guard = self._admission.guard() if self._admission else contextlib.nullcontext()
            async with guard:
                if self._admission is not None and not await self._admission.enabled(source_id):
                    return PollOutcome(
                        source_id, ok=False, error="Disabled before results were admitted."
                    )
                if batch is not None and isinstance(connector, GuardedFeedConnector):
                    async with connector.release_guard(batch.generation) as current:
                        if not current:
                            raise FeedUnavailable("Connection changed before publication.")
                        outcome = await self._publish(connector, raw, started)
                else:
                    outcome = await self._publish(connector, raw, started)
                return outcome
        except FeedDeferred as exc:
            entry = self._health.record_deferred(source_id, str(exc), started, exc.retry_at)
            await self._bus.publish(BusMessage("source.health", {"health": entry}))
            return PollOutcome(source_id, ok=False, error=entry.last_error)
        except FeedUnavailable as exc:
            return PollOutcome(source_id, ok=False, error=str(exc))
        except Exception as exc:
            if isinstance(connector, GuardedFeedConnector):
                return await self._guarded_failure(connector, generation, started)
            return await self._failure(source_id, f"{type(exc).__name__}: {exc}", started)

    async def _guarded_failure(
        self, connector: GuardedFeedConnector, generation: int | None, started: datetime
    ) -> PollOutcome:
        source_id = connector.spec.id
        if generation is None:
            return PollOutcome(source_id, ok=False, error="Connection configuration unavailable.")
        try:
            guard = self._admission.guard() if self._admission else contextlib.nullcontext()
            async with guard, connector.release_guard(generation) as current:
                if not current:
                    return PollOutcome(
                        source_id, ok=False, error="Connection changed before publication."
                    )
                return await self._failure(
                    source_id, "The configured source could not be fetched.", started
                )
        except Exception:
            # Unverifiable authority is not evidence of upstream failure. Keep the
            # loop alive without publishing health under an unknown configuration.
            return PollOutcome(source_id, ok=False, error="Connection verification unavailable.")

    async def _failure(self, source_id: str, error: str, started: datetime) -> PollOutcome:
        entry = self._health.record_failure(source_id, error, started)
        await self._bus.publish(BusMessage("source.health", {"health": entry}))
        return PollOutcome(source_id, ok=False, error=entry.last_error)

    async def _publish(
        self, connector: FeedConnector, raw: list[Event], started: datetime
    ) -> PollOutcome:
        """No external requests here; caller retains the shared admission/release guard."""
        source_id = connector.spec.id
        events = await self._pipeline.run_cooperatively(raw)
        result = self._store.upsert(events)
        finished = self._clock.now()
        latency_ms = (finished - started).total_seconds() * 1000
        entry = self._health.record_success(
            source_id,
            len(events),
            latency_ms,
            finished,
            connector.spec.poll_interval,
            warning=connector.warning if isinstance(connector, DiagnosticFeedConnector) else None,
        )
        if result.changed_ids:
            changed = set(result.changed_ids)
            fresh = [e for e in events if e.id in changed]
            if self._grader is not None:
                fresh = self._regraded(fresh)
            await self._bus.publish(
                BusMessage("event.upsert", {"source_id": source_id, "events": fresh})
            )
        await self._bus.publish(BusMessage("source.health", {"health": entry}))
        return PollOutcome(source_id, ok=True, fetched=len(events), changed=result.changed)

    def _regraded(self, fresh: list[Event]) -> list[Event]:
        """Grades the batch in context and merges any neighbours whose grade moved."""
        assert self._grader is not None  # noqa: S101
        latest = {event.id: event for event in fresh}
        for event in self._grader.regrade(fresh):
            latest[event.id] = event
        for event_id in list(latest):
            stored = self._store.get(event_id)
            if stored is not None:
                latest[event_id] = stored
        return list(latest.values())

    async def _run_connector(self, connector: FeedConnector) -> None:
        interval = connector.spec.poll_interval.total_seconds()
        # Spread the first polls so a restart does not hit every upstream at once.
        await self._sleep(random.uniform(0, min(5.0, interval * self._jitter)))  # noqa: S311 # nosec B311
        while not self._stopping.is_set():
            await self.poll_once(connector)
            entry = self._health.get(connector.spec.id)
            if entry.status is SourceStatus.DISABLED:
                return
            delay = interval
            if entry.next_poll_at is not None:
                delay = max(1.0, (entry.next_poll_at - self._clock.now()).total_seconds())
            await self._sleep(
                delay * random.uniform(1 - self._jitter, 1 + self._jitter)  # noqa: S311 # nosec B311
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

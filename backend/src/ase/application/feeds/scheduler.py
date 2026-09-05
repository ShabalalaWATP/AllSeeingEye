"""Runs every connector on its own interval with timeouts, backoff and health tracking."""

from __future__ import annotations

import asyncio
import contextlib
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Pipeline
from ase.application.ports import Clock
from ase.application.ports.feeds import BusMessage, EventBus, EventStore, FeedConnector
from ase.domain.errors import NotFound

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
        fetch_timeout: timedelta = timedelta(seconds=60),
        prune_interval: timedelta = timedelta(seconds=60),
        jitter: float = 0.1,
        sleep: SleepFn = asyncio.sleep,
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
        self._tasks: dict[str, asyncio.Task[None]] = {}
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
        tasks = [*self._tasks.values()]
        if self._prune_task is not None:
            tasks.append(self._prune_task)
        for task in tasks:
            task.cancel()
        for task in tasks:
            # Shutdown must never raise, whatever a connector was doing.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._tasks.clear()
        self._prune_task = None

    def resume(self, source_id: str) -> None:
        """Re-enable a source an administrator has reset after the breaker disabled it."""
        connector = self._connectors.get(source_id)
        if connector is None:
            raise NotFound()
        self._health.reset(source_id)
        task = self._tasks.get(source_id)
        if self.running and (task is None or task.done()):
            self._tasks[source_id] = asyncio.create_task(self._run_connector(connector))

    async def poll_once(self, connector: FeedConnector) -> PollOutcome:
        source_id = connector.spec.id
        started = self._clock.now()
        try:
            async with asyncio.timeout(self._fetch_timeout.total_seconds()):
                raw = await connector.fetch()
            events = self._pipeline.run(raw)
            result = self._store.upsert(events)
        except Exception as exc:
            entry = self._health.record_failure(source_id, f"{type(exc).__name__}: {exc}", started)
            await self._bus.publish(BusMessage("source.health", {"health": entry}))
            return PollOutcome(source_id, ok=False, error=entry.last_error)
        finished = self._clock.now()
        latency_ms = (finished - started).total_seconds() * 1000
        entry = self._health.record_success(
            source_id, len(events), latency_ms, finished, connector.spec.poll_interval
        )
        if result.changed_ids:
            changed = set(result.changed_ids)
            await self._bus.publish(
                BusMessage(
                    "event.upsert",
                    {"source_id": source_id, "events": [e for e in events if e.id in changed]},
                )
            )
        await self._bus.publish(BusMessage("source.health", {"health": entry}))
        return PollOutcome(source_id, ok=True, fetched=len(events), changed=result.changed)

    async def _run_connector(self, connector: FeedConnector) -> None:
        interval = connector.spec.poll_interval.total_seconds()
        # Spread the first polls so a restart does not hit every upstream at once.
        await self._sleep(random.uniform(0, min(5.0, interval * self._jitter)))  # noqa: S311
        while not self._stopping.is_set():
            await self.poll_once(connector)
            entry = self._health.get(connector.spec.id)
            if entry.status is SourceStatus.DISABLED:
                return
            delay = interval
            if entry.next_poll_at is not None:
                delay = max(1.0, (entry.next_poll_at - self._clock.now()).total_seconds())
            await self._sleep(delay * random.uniform(1 - self._jitter, 1 + self._jitter))  # noqa: S311

    async def _prune_loop(self) -> None:
        while not self._stopping.is_set():
            await self._sleep(self._prune_interval.total_seconds())
            result = self._store.prune(self._clock.now())
            if result.ids:
                await self._bus.publish(
                    BusMessage("event.expire", {"ids": result.ids, "count": len(result.ids)})
                )

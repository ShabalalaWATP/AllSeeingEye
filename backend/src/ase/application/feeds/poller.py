"""One bounded poll of one source: fetch, final admission, publication and health."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta

from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.poll_outcome import PollOutcome
from ase.application.feeds.poll_scope import poll_scope
from ase.application.ports import Clock
from ase.application.ports.cooperative_feeds import CooperativeEventStore, CooperativeGrader
from ase.application.ports.feed_diagnostics import (
    CoverageFeedConnector,
    DiagnosticFeedConnector,
    FeedBlocked,
    FeedDeferred,
    FeedRateLimited,
)
from ase.application.ports.feed_release import FeedUnavailable, FetchedBatch, GuardedFeedConnector
from ase.application.ports.feeds import BusMessage, EventBus, EventStore, FeedConnector, Grader
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.events import Event


class FeedPoller:
    def __init__(
        self,
        pipeline: Pipeline,
        store: EventStore,
        bus: EventBus,
        health: HealthRegistry,
        clock: Clock,
        *,
        fetch_timeout: timedelta | None,
        grader: Grader | None,
        admission: SourceAdmission | None,
        processing_timeout: timedelta,
        fetch_concurrency: int,
    ) -> None:
        if fetch_concurrency < 1:
            raise ValueError("fetch_concurrency must be at least 1")
        self._pipeline = pipeline
        self._store = store
        self._bus = bus
        self._health = health
        self._clock = clock
        self._fetch_timeout = fetch_timeout
        self._grader = grader
        self._admission = admission
        self._processing_seconds = processing_timeout.total_seconds()
        # Each response may be several megabytes; bound how many are in flight at once.
        self._fetch_slots = asyncio.Semaphore(fetch_concurrency)
        self._retry_not_before: dict[str, datetime] = {}

    async def poll_once(self, connector: FeedConnector) -> PollOutcome:
        """Per-poll side effects, such as conditional validators, land only after publication."""
        source_id = connector.spec.id
        deadline = self._retry_not_before.get(source_id)
        if deadline is not None:
            if self._clock.now() < deadline:
                self._health.get(source_id).next_poll_at = deadline
                return PollOutcome(
                    source_id, ok=False, error="Waiting for the upstream retry time."
                )
            self._retry_not_before.pop(source_id)
        with poll_scope() as scope:
            outcome = await self._poll(connector)
            if outcome.ok:
                scope.commit()
            return outcome

    def _fetch_seconds(self, source_id: str) -> float:
        # World FIRMS responses have exceeded 60s in measured collection.
        # Explicit caller timeouts still override these fixed-source defaults.
        if self._fetch_timeout is not None:
            return self._fetch_timeout.total_seconds()
        return 120 if source_id in {"firms_viirs_noaa20", "firms_viirs_noaa21"} else 60

    def _processing_deadline(self) -> asyncio.Timeout:
        """Bounds work after the fetch, including waits for the shared release guard."""
        return asyncio.timeout_at(asyncio.get_running_loop().time() + self._processing_seconds)

    async def _poll(self, connector: FeedConnector) -> PollOutcome:
        source_id = connector.spec.id
        started = self._clock.now()
        generation: int | None = None
        batch: FetchedBatch | None = None
        try:
            if self._admission is not None and not await self._admission.enabled(source_id):
                raise FeedUnavailable("Disabled by administrator.")
            # Waiting for a fetch slot does not count against the upstream's deadline.
            async with self._fetch_slots:
                async with asyncio.timeout(self._fetch_seconds(source_id)):
                    if isinstance(connector, GuardedFeedConnector):
                        generation = await connector.current_generation()
                        batch = await connector.fetch_batch()
                    raw = batch.events if batch is not None else await connector.fetch()
            deadline = self._processing_deadline()
            try:
                async with deadline:
                    return await self._release(connector, raw, batch, started)
            except TimeoutError:
                if not deadline.expired():
                    raise
            # A hung guard, lock or oversized batch fails this source, never the scheduler.
            error = f"Processing exceeded its {self._processing_seconds:g}-second deadline."
            return await self._failure(source_id, error, started)
        except (FeedDeferred, FeedRateLimited) as exc:
            return await self._slowed(connector, exc, generation, self._clock.now())
        except FeedUnavailable as exc:
            return PollOutcome(source_id, ok=False, error=str(exc))
        except Exception as exc:
            if isinstance(connector, GuardedFeedConnector):
                return await self._guarded_failure(connector, generation, started)
            return await self._failure(source_id, f"{type(exc).__name__}: {exc}", started)

    async def _release(
        self,
        connector: FeedConnector,
        raw: list[Event],
        batch: FetchedBatch | None,
        started: datetime,
    ) -> PollOutcome:
        """Only the final admission read and publication hold the process-wide guard."""
        source_id = connector.spec.id
        # Normalisation reads no shared state, so it never delays another feed's release.
        events = await self._pipeline.run_cooperatively(raw)
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
                    return await self._publish(connector, events, started)
            return await self._publish(connector, events, started)

    async def _slowed(
        self,
        connector: FeedConnector,
        exc: FeedDeferred | FeedRateLimited,
        generation: int | None,
        started: datetime,
    ) -> PollOutcome:
        """A deliberate deferral or an upstream throttle schedules the next attempt."""
        source_id = connector.spec.id
        if isinstance(exc, FeedDeferred):
            entry = self._health.record_deferred(
                source_id,
                str(exc),
                started,
                exc.retry_at,
                blocked=isinstance(exc, FeedBlocked),
            )
        elif isinstance(connector, GuardedFeedConnector):
            return await self._guarded_failure(connector, generation, started, rate_limit=exc)
        else:
            entry = self._health.record_rate_limited(
                source_id, f"{type(exc).__name__}: {exc}", started, exc.retry_after
            )
            if entry.next_poll_at is not None:
                self._retry_not_before[source_id] = entry.next_poll_at
        await self._bus.publish(BusMessage("source.health", {"health": entry}))
        return PollOutcome(source_id, ok=False, error=entry.last_error)

    async def _guarded_failure(
        self,
        connector: GuardedFeedConnector,
        generation: int | None,
        started: datetime,
        *,
        rate_limit: FeedRateLimited | None = None,
    ) -> PollOutcome:
        source_id = connector.spec.id
        if generation is None:
            return PollOutcome(source_id, ok=False, error="Connection configuration unavailable.")
        try:
            guard = self._admission.guard() if self._admission else contextlib.nullcontext()
            async with (
                self._processing_deadline(),
                guard,
                connector.release_guard(generation) as current,
            ):
                if not current:
                    return PollOutcome(
                        source_id, ok=False, error="Connection changed before publication."
                    )
                if rate_limit is not None:
                    entry = self._health.record_rate_limited(
                        source_id,
                        "The configured source requested a slower retry.",
                        started,
                        rate_limit.retry_after,
                    )
                    if entry.next_poll_at is not None:
                        self._retry_not_before[source_id] = entry.next_poll_at
                    await self._bus.publish(BusMessage("source.health", {"health": entry}))
                    return PollOutcome(source_id, ok=False, error=entry.last_error)
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
        self, connector: FeedConnector, events: list[Event], started: datetime
    ) -> PollOutcome:
        """No external requests here; caller retains the shared admission/release guard.

        Upsert, contextual regrade and the bus message stay together under that guard:
        grading rewrites neighbouring records in the shared store and the message
        carries graded events, so splitting them could publish after a disable commits.
        """
        source_id = connector.spec.id
        result = (
            await self._store.upsert_cooperatively(events)
            if isinstance(self._store, CooperativeEventStore)
            else self._store.upsert(events)
        )
        finished = self._clock.now()
        latency_ms = (finished - started).total_seconds() * 1000
        entry = self._health.record_success(
            source_id,
            len(events),
            latency_ms,
            finished,
            connector.spec.poll_interval,
            warning=connector.warning if isinstance(connector, DiagnosticFeedConnector) else None,
            coverage_warning=(
                connector.coverage_warning if isinstance(connector, CoverageFeedConnector) else None
            ),
        )
        if result.changed_ids:
            changed = set(result.changed_ids)
            fresh = [e for e in events if e.id in changed]
            if self._grader is not None:
                fresh = await self._regraded(fresh)
            await self._bus.publish(
                BusMessage("event.upsert", {"source_id": source_id, "events": fresh})
            )
        await self._bus.publish(BusMessage("source.health", {"health": entry}))
        return PollOutcome(source_id, ok=True, fetched=len(events), changed=result.changed)

    async def _regraded(self, fresh: list[Event]) -> list[Event]:
        """Grades the batch in context and merges any neighbours whose grade moved."""
        assert self._grader is not None  # noqa: S101
        latest = {event.id: event for event in fresh}
        graded = (
            await self._grader.regrade_cooperatively(fresh)
            if isinstance(self._grader, CooperativeGrader)
            else self._grader.regrade(fresh)
        )
        for event in graded:
            latest[event.id] = event
        for event_id in list(latest):
            stored = self._store.get(event_id)
            if stored is not None:
                latest[event_id] = stored
            else:
                latest.pop(event_id)
        return list(latest.values())

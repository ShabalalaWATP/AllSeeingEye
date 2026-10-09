"""The evaluator: every minute, run each enabled indicator over the live store and route alerts.

An alert is stored, published on the bus (the stream carries it to open pages), handed to the
notifier (a webhook when one is configured) and, when the indicator names a report template,
given a durable report admission intent in the alert transaction. A separate worker admits
reports, so model latency and failures never delay the next rule or evaluation cycle.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ase.application.ports import Clock
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.feeds import BusMessage, EventBus, EventQuery, EventStore
from ase.application.ports.warning import AlertNotifier, IndicatorBaselineStore, WarningStore
from ase.application.warning.report_snapshot import capture_report
from ase.application.worker_progress import run_cycle
from ase.domain.errors import RateLimited
from ase.domain.grading import SourceProfile
from ase.domain.warning import ALERT_RETENTION, Alert, Firing, Indicator, alert_from, evaluate

log = logging.getLogger(__name__)

INTERVAL = timedelta(seconds=60)
MAX_ADMISSION_RETRIES = 2
ADMISSION_RETRY_SECONDS = 1.0
SleepFn = Callable[[float], Awaitable[None]]


async def evaluate_candidates(
    store: EventStore,
    indicator: Indicator,
    now: datetime,
    last: datetime | None,
    alerted: frozenset[str] = frozenset(),
) -> Firing | None:
    """Count every match on one admitted snapshot; bound only the exported evidence."""
    # Store intervals are half-open. The next representable instant includes exactly
    # now, without admitting a future publication. At datetime.max no later instant exists.
    until = now + datetime.resolution if now < datetime.max.replace(tzinfo=UTC) else None
    query = EventQuery(
        categories=frozenset(indicator.categories),
        research_area=indicator.research_area,
        bbox=indicator.bbox if indicator.research_area is None else None,
        since=now - indicator.window,
        until=until,
        limit=None,
    )
    # Country unions and remaining predicates are evaluated together on this snapshot.
    if isinstance(store, CooperativeEventReader):
        return await store.read_cooperatively(
            query,
            lambda events: evaluate(indicator, events, now, last, alerted),
            admission_key="internal:exact-indicators",
        )
    return evaluate(indicator, store.query(query), now, last, alerted)


class IndicatorEvaluator:
    def __init__(
        self,
        store: EventStore,
        warnings: WarningStore,
        bus: EventBus,
        notifier: AlertNotifier,
        clock: Clock,
        *,
        baselines: IndicatorBaselineStore | None = None,
        source_profiles: Mapping[str, SourceProfile] | None = None,
        interval: timedelta = INTERVAL,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._store = store
        self._warnings = warnings
        self._bus = bus
        self._notifier = notifier
        self._clock = clock
        self._baselines = baselines
        self._source_profiles = source_profiles or {}
        self._interval = interval
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def run_once(self) -> list[Alert]:
        now = self._clock.now()
        fired: list[Alert] = []
        admission_retries = MAX_ADMISSION_RETRIES
        for indicator in await self._warnings.enabled_indicators():
            if not await self._warnings.can_run(indicator):
                continue
            latest = await self._warnings.latest_alert(indicator.id)
            last = None if latest is None else latest.fired_at
            alerted = await self._alerted(indicator, now, last)
            while True:
                try:
                    firing = await self._evaluate(indicator, now, last, alerted)
                    break
                except RateLimited:
                    if admission_retries == 0:
                        log.warning(
                            "indicator_evaluation_deferred", extra={"indicator": indicator.name}
                        )
                        firing = None
                        break
                    # A cycle-wide budget prevents saturation multiplying delays by rule count.
                    admission_retries -= 1
                    await self._sleep(ADMISSION_RETRY_SECONDS)
            if firing is None:
                continue
            alert = alert_from(indicator, firing, uuid4(), now)
            if indicator.baseline_ratio is not None and self._baselines is not None:
                baseline = await self._baselines.summary(indicator, now)
                if not baseline.ready or baseline.mean is None:
                    continue
                alert = replace(
                    alert, baseline_mean=baseline.mean, baseline_ratio=firing.count / baseline.mean
                )
            snapshot = None
            if indicator.report_template is not None:
                try:
                    snapshot = capture_report(indicator, alert, firing, self._source_profiles)
                except ValueError:
                    alert = replace(
                        alert, report_status="failed", report_error="evidence_unavailable"
                    )
            if not await self._warnings.add_alert(alert, indicator, report_snapshot=snapshot):
                continue
            log.info("alert_fired", extra={"indicator": indicator.name, "count": alert.count})
            await self._route(alert, indicator)
            fired.append(alert)
        pruned = await self._warnings.prune(now - ALERT_RETENTION)
        if pruned:
            log.info("alerts_pruned", extra={"count": pruned})
        return fired

    async def _alerted(
        self, rule: Indicator, now: datetime, last: datetime | None
    ) -> frozenset[str]:
        """Evidence already cited inside the window; skipped while cooling down or unneeded."""
        since = now - rule.window
        if last is None or last < since or now - last < rule.cooldown:
            return frozenset()  # No alert inside the window, or evaluation stops at the cooldown.
        if rule.baseline_ratio is not None:
            return frozenset()  # Ratio rules compare the full hourly count with their baseline.
        return await self._warnings.alerted_event_ids(rule.id, since)

    async def _evaluate(
        self,
        rule: Indicator,
        now: datetime,
        last: datetime | None,
        alerted: frozenset[str] = frozenset(),
    ) -> Firing | None:
        if self._baselines is None:
            return (
                None
                if rule.baseline_ratio is not None
                else await evaluate_candidates(self._store, rule, now, last, alerted)
            )
        hourly = await evaluate_candidates(
            self._store,
            replace(rule, threshold=0, window_minutes=60),
            now,
            None,
        )
        if hourly is not None:
            await self._baselines.record(
                rule, now.replace(minute=0, second=0, microsecond=0), hourly.count
            )
        if rule.baseline_ratio is None:
            return await evaluate_candidates(self._store, rule, now, last, alerted)
        baseline = await self._baselines.summary(rule, now)
        if not baseline.ready or baseline.mean is None or hourly is None:
            return None
        if last is not None and now - last < rule.cooldown:
            return None
        return (
            hourly
            if hourly.count >= rule.threshold
            and hourly.count / baseline.mean >= rule.baseline_ratio
            else None
        )

    async def _route(self, alert: Alert, indicator: Indicator) -> None:
        if not await self._warnings.can_run(indicator):
            return
        await self._bus.publish(BusMessage("alert", {"alert": alert}))
        try:
            if not await self._warnings.can_run(indicator):
                return
            await self._notifier.notify(alert, indicator)
        except Exception:
            log.exception("alert_notify_failed", extra={"indicator": indicator.name})

    async def start(self) -> None:
        if self._task is None:
            self._stopping.clear()
            self._task = asyncio.create_task(self._run(), name="indicator-evaluator")

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
                await run_cycle("evaluator", self._interval.total_seconds(), self.run_once)
            except Exception:
                log.exception("evaluator_cycle_failed")
            await self._sleep(self._interval.total_seconds())

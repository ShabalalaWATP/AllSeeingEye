"""The evaluator: every minute, run each enabled indicator over the live store and route alerts.

An alert is stored, published on the bus (the stream carries it to open pages), handed to the
notifier (a webhook when one is configured) and, when the indicator names a report template,
turned into a report through the reporter the container supplies. Failures in any route are
logged and never stop the others.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ase.application.ports import Clock
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.feeds import BusMessage, EventBus, EventQuery, EventStore
from ase.application.ports.warning import AlertNotifier, WarningStore
from ase.domain.errors import RateLimited
from ase.domain.warning import ALERT_RETENTION, Alert, Firing, Indicator, alert_from, evaluate

log = logging.getLogger(__name__)

INTERVAL = timedelta(seconds=60)
MAX_ADMISSION_RETRIES = 2
ADMISSION_RETRY_SECONDS = 1.0
Reporter = Callable[[Indicator, Alert], Awaitable[UUID | None]]
SleepFn = Callable[[float], Awaitable[None]]


async def evaluate_candidates(
    store: EventStore, indicator: Indicator, now: datetime, last: datetime | None
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
            lambda events: evaluate(indicator, events, now, last),
            admission_key="internal:exact-indicators",
        )
    return evaluate(indicator, store.query(query), now, last)


class IndicatorEvaluator:
    def __init__(
        self,
        store: EventStore,
        warnings: WarningStore,
        bus: EventBus,
        notifier: AlertNotifier,
        clock: Clock,
        *,
        reporter: Reporter | None = None,
        interval: timedelta = INTERVAL,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._store = store
        self._warnings = warnings
        self._bus = bus
        self._notifier = notifier
        self._clock = clock
        self._reporter = reporter
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
            while True:
                try:
                    firing = await evaluate_candidates(self._store, indicator, now, last)
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
            if not await self._warnings.add_alert(alert, indicator):
                continue
            log.info("alert_fired", extra={"indicator": indicator.name, "count": alert.count})
            await self._route(alert, indicator)
            fired.append(alert)
        pruned = await self._warnings.prune(now - ALERT_RETENTION)
        if pruned:
            log.info("alerts_pruned", extra={"count": pruned})
        return fired

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
        if self._reporter is None or indicator.report_template is None:
            return
        try:
            if not await self._warnings.can_run(indicator):
                return
            report_id = await self._reporter(indicator, alert)
        except Exception:
            log.exception("alert_report_failed", extra={"indicator": indicator.name})
            return
        if report_id is not None:
            await self._warnings.attach_report(alert.id, report_id)

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
                await self.run_once()
            except Exception:
                log.exception("evaluator_cycle_failed")
            await self._sleep(self._interval.total_seconds())

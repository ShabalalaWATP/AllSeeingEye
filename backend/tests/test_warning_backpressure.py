"""Public read saturation has one bounded warning retry budget per cycle."""

import asyncio
import threading
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.application.warning.evaluator import IndicatorEvaluator
from ase.domain.events import Event
from ase.domain.warning import ALERT_RETENTION, Alert, Indicator
from helpers import FakeClock
from test_warning import NOW
from test_warning_volume import matching_event, scoped_rule


class RecordingWarnings:
    def __init__(self) -> None:
        self.rules = [scoped_rule("global"), scoped_rule("country")]
        self.considered: list[UUID] = []
        self.alerts: list[Alert] = []
        self.pruned_before: list[datetime] = []

    async def enabled_indicators(self) -> list[Indicator]:
        return self.rules

    async def can_run(self, indicator: Indicator) -> bool:
        return indicator in self.rules

    async def latest_alert(self, indicator_id: UUID) -> Alert | None:
        self.considered.append(indicator_id)
        return None

    async def add_alert(self, alert: Alert, indicator: Indicator, *, report_snapshot=None) -> bool:
        assert alert.indicator_id == indicator.id
        self.alerts.append(alert)
        return True

    async def attach_report(self, alert_id: UUID, report_id: UUID) -> bool:
        raise AssertionError("These warning rules do not request reports")

    async def prune(self, before: datetime) -> int:
        self.pruned_before.append(before)
        return 0


@asynccontextmanager
async def saturated_readers(
    store: InMemoryEventStore,
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """Occupy real admission with four users, each holding two public reads."""
    entered, release = threading.Event(), threading.Event()

    def block(events: list[Event]) -> list[Event]:
        entered.set()
        assert release.wait(10), "The fixture must release its admitted worker"
        return events

    readers = [
        asyncio.create_task(
            store.read_cooperatively(
                EventQuery(), block, admission_key=f"user:fixture-{index // 2}"
            )
        )
        for index in range(8)
    ]

    async def drain() -> None:
        release.set()
        await asyncio.gather(*readers)

    try:
        async with asyncio.timeout(5):
            while not entered.is_set() or store._waiting_reads != 8:
                await asyncio.sleep(0)
        assert store._waiting_reads_by_key == {f"user:fixture-{index}": 2 for index in range(4)}
        assert not any(reader.done() for reader in readers)
        yield drain
    finally:
        await drain()
        assert store._waiting_reads == 0
        assert store._waiting_reads_by_key == {}


def make_evaluator(
    store: InMemoryEventStore,
    warnings: RecordingWarnings,
    sleep: Callable[[float], Awaitable[None]],
) -> IndicatorEvaluator:
    return IndicatorEvaluator(
        store,
        warnings,
        InMemoryEventBus(),
        AsyncMock(),
        FakeClock(NOW),
        sleep=sleep,
    )


async def test_queue_draining_during_first_backoff_allows_both_rules_to_fire() -> None:
    store = InMemoryEventStore()
    store.upsert([matching_event("match")])
    warnings = RecordingWarnings()
    sleeps: list[float] = []
    async with saturated_readers(store) as drain:

        async def backoff(seconds: float) -> None:
            sleeps.append(seconds)
            await drain()

        fired = await make_evaluator(store, warnings, backoff).run_once()

    assert sleeps == [1.0]
    assert warnings.considered == [rule.id for rule in warnings.rules]
    assert [alert.indicator_id for alert in fired] == [rule.id for rule in warnings.rules]
    assert [alert.count for alert in fired] == [1, 1]
    assert warnings.alerts == fired
    assert warnings.pruned_before == [NOW - ALERT_RETENTION]


@pytest.mark.parametrize("cycles", [1, 2])
async def test_sustained_saturation_shares_two_retries_and_still_prunes(cycles: int) -> None:
    store = InMemoryEventStore()
    store.upsert([matching_event("match")])
    warnings = RecordingWarnings()
    sleeps: list[float] = []

    async def backoff(seconds: float) -> None:
        sleeps.append(seconds)
        await asyncio.sleep(0)

    evaluator = make_evaluator(store, warnings, backoff)
    async with saturated_readers(store):
        for cycle in range(cycles):
            assert await evaluator.run_once() == []
            assert sleeps == [1.0, 1.0] * (cycle + 1)
            assert store._waiting_reads == 8

    assert warnings.considered == [rule.id for rule in warnings.rules] * cycles
    assert warnings.alerts == []
    assert warnings.pruned_before == [NOW - ALERT_RETENTION] * cycles


async def test_cancellation_during_backoff_does_not_wait_for_or_leak_public_readers() -> None:
    store = InMemoryEventStore()
    warnings = RecordingWarnings()
    sleeping = asyncio.Event()
    sleeps: list[float] = []

    async def backoff(seconds: float) -> None:
        sleeps.append(seconds)
        sleeping.set()
        await asyncio.Event().wait()

    async with saturated_readers(store):
        pending = asyncio.create_task(make_evaluator(store, warnings, backoff).run_once())
        try:
            async with asyncio.timeout(5):
                while not sleeping.is_set():
                    if pending.done():
                        await pending  # Surface an escaped admission error immediately.
                    await asyncio.sleep(0)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                async with asyncio.timeout(5):
                    await pending
            # Cancellation completed while every fixture read remains blocked.
            assert store._waiting_reads == 8
            assert store._waiting_reads_by_key == {f"user:fixture-{index}": 2 for index in range(4)}
        finally:
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending

    assert sleeps == [1.0]
    assert warnings.alerts == []

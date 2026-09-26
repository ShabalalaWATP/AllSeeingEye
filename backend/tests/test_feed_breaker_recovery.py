"""The circuit breaker pauses a failing feed, then probes it after a doubling cool-down."""

import asyncio
from datetime import timedelta

from ase.application.feeds.health import CircuitBreaker, HealthRegistry, SourceStatus
from feeds_helpers import NOW, FakeClock, FakeConnector
from test_feed_scheduler_reliability import Admission, connector, scheduler_for


def test_breaker_cooldown_doubles_to_a_ceiling_and_success_clears_it() -> None:
    registry = HealthRegistry(breaker=CircuitBreaker(disable_after=2))
    registry.record_failure("s", "boom", NOW)
    tripped = registry.record_failure("s", "boom", NOW)
    assert tripped.status is SourceStatus.DISABLED and tripped.trips == 1
    assert tripped.next_poll_at == NOW + timedelta(hours=6)
    for hours in (12, 24, 24):
        probe = registry.record_failure("s", "boom", NOW)
        assert probe.status is SourceStatus.DISABLED
        assert probe.next_poll_at == NOW + timedelta(hours=hours)
    healthy = registry.record_success("s", 1, 1.0, NOW, timedelta(minutes=5))
    assert healthy.status is SourceStatus.HEALTHY and healthy.trips == 0
    registry.record_failure("s", "boom", NOW)
    assert registry.record_failure("s", "boom", NOW).next_poll_at == NOW + timedelta(hours=6)


def breaker_loop(target: FakeConnector, admission: Admission | None = None):
    clock = FakeClock(NOW)
    health = HealthRegistry(
        breaker=CircuitBreaker(disable_after=2, base_backoff=timedelta(seconds=5))
    )
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if seconds == 6 * 3600 and admission is not None:
            admission.disabled.add(target.spec.id)  # an administrator switches it off
        clock.advance(timedelta(seconds=seconds))
        if len(sleeps) == 6:
            scheduler._stopping.set()
        await asyncio.sleep(0)

    scheduler, store = scheduler_for(
        [target], clock=clock, health=health, admission=admission, sleep=sleep, jitter=0.0
    )
    return scheduler, store, health, sleeps


async def test_paused_source_probes_after_its_cooldown_and_recovers() -> None:
    target = connector("flaky")
    target.failures = 3  # two trip the breaker, then the first probe fails too
    scheduler, store, health, sleeps = breaker_loop(target)
    await asyncio.wait_for(scheduler._run_connector(target, first_delay=0.0), 2)
    assert sleeps[:5] == [0.0, 5.0, 6 * 3600, 12 * 3600, 60.0]
    entry = health.get("flaky")
    assert entry.status is SourceStatus.HEALTHY and entry.trips == 0
    assert target.calls == 5 and store.stats().total == 1


async def test_cooldown_probe_never_clears_an_administrator_disable() -> None:
    target = connector("switched_off")
    target.failures = 2
    admission = Admission()
    scheduler, store, health, sleeps = breaker_loop(target, admission)
    await asyncio.wait_for(scheduler._run_connector(target, first_delay=0.0), 2)
    # The probe found the administrator's switch off: no fetch, no health change,
    # and the loop keeps the ordinary cadence instead of retrying every second.
    assert target.calls == 2 and store.stats().total == 0
    assert sleeps == [0.0, 5.0, 6 * 3600, 60.0, 60.0, 60.0]
    assert health.get("switched_off").status is SourceStatus.DISABLED
    assert not await admission.enabled("switched_off")

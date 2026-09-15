"""HTTP 429 honours a bounded Retry-After, never disables a source, and shared hosts are paced."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import httpx
import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.host_pacing import DEFAULT_HOST_INTERVALS, HostPacer
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.http_contracts import (
    FeedHttpStatusError,
    FeedRateLimitedError,
    parse_retry_after,
    status_error,
)
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import CircuitBreaker, HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feed_diagnostics import FeedRateLimited
from ase.domain.events import Event
from feeds_helpers import NOW, FakeClock, make_spec

URL = "https://93.184.216.34/feed"


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"Retry-After": "120"}, timedelta(seconds=120)),
        ({"Retry-After": "2.5"}, timedelta(seconds=2.5)),
        ({"Retry-After": "0"}, timedelta(seconds=1)),
        ({"Retry-After": "86400"}, timedelta(hours=1)),
        ({"Retry-After": "Sat, 05 Sep 2026 00:10:00 GMT"}, timedelta(minutes=10)),
        ({"Retry-After": "Fri, 04 Sep 2026 23:00:00 GMT"}, timedelta(seconds=1)),
        ({"X-RateLimit-Reset": "40"}, timedelta(seconds=40)),
        ({"X-RateLimit-Reset": str(int(NOW.timestamp()) + 300)}, timedelta(minutes=5)),
        ({"Retry-After": "9" * 30}, None),
        ({"Retry-After": "9" * 40}, None),
        ({"Retry-After": "soon"}, None),
        ({"Retry-After": "-5"}, None),
        ({}, None),
    ],
)
def test_retry_after_is_parsed_and_bounded(headers: dict[str, str], expected) -> None:
    assert parse_retry_after(httpx.Headers(headers), NOW) == expected


def test_only_429_becomes_a_rate_limit() -> None:
    limited = status_error(429, URL, httpx.Headers({"Retry-After": "30"}))
    assert isinstance(limited, FeedRateLimitedError) and isinstance(limited, FeedRateLimited)
    assert limited.retry_after == timedelta(seconds=30) and limited.status_code == 429
    other = status_error(503, URL, httpx.Headers({"Retry-After": "30"}))
    assert type(other) is FeedHttpStatusError


async def test_client_raises_the_rate_limit_with_its_wait() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "90"}, content=b"<html>slow</html>")

    client = FeedHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedRateLimitedError) as caught:
            await client.get_json(URL)
        assert caught.value.retry_after == timedelta(seconds=90)
        assert "slow" not in str(caught.value)
    finally:
        await client.aclose()


def test_health_waits_for_the_longer_of_backoff_and_retry_after_and_never_disables() -> None:
    registry = HealthRegistry(breaker=CircuitBreaker(disable_after=2))
    first = registry.record_rate_limited("s", "HTTP 429", NOW, timedelta(minutes=10))
    assert first.status is SourceStatus.DEGRADED
    assert first.next_poll_at == NOW + timedelta(minutes=10)
    second = registry.record_rate_limited("s", "HTTP 429", NOW, None)
    assert second.next_poll_at == NOW + timedelta(minutes=2)  # exponential backoff
    for _ in range(20):
        entry = registry.record_rate_limited("s", "HTTP 429", NOW, timedelta(hours=5))
    assert entry.status is SourceStatus.DEGRADED
    assert entry.next_poll_at == NOW + timedelta(hours=1)


class ThrottledConnector:
    def __init__(self, retry_after: timedelta | None) -> None:
        self.spec = make_spec("throttled", seconds=120)
        self.retry_after = retry_after

    async def fetch(self) -> list[Event]:
        raise FeedRateLimitedError("https://api.example/v2/list", self.retry_after)


async def test_scheduler_sleeps_until_the_upstream_allows_another_request() -> None:
    clock = FakeClock(NOW)
    health = HealthRegistry(breaker=CircuitBreaker(disable_after=2))
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) >= 6:
            await scheduler.stop()
        await asyncio.sleep(0)

    connector = ThrottledConnector(timedelta(minutes=15))
    scheduler = FeedScheduler(
        [connector],
        Pipeline([Normaliser()]),
        InMemoryEventStore(),
        InMemoryEventBus(),
        health,
        clock,
        jitter=0.0,
        prune_interval=timedelta(hours=2),
        sleep=fake_sleep,
    )
    outcome = await scheduler.poll_once(connector)
    assert not outcome.ok and "HTTP 429" in (outcome.error or "")
    entry = health.get("throttled")
    assert entry.next_poll_at == NOW + timedelta(minutes=15)
    assert entry.status is SourceStatus.DEGRADED
    await scheduler.start()
    task = next(iter(scheduler._tasks.values()))
    with pytest.raises(asyncio.CancelledError):
        await task
    # Not the 120-second cadence or the 60-second breaker backoff, and never disabled.
    assert sleeps.count(900.0) >= 2 and set(sleeps) <= {0.0, 900.0, 7200.0}
    assert health.get("throttled").status is SourceStatus.DEGRADED


async def test_host_pacer_spaces_request_starts_for_listed_hosts_only() -> None:
    now = [100.0]
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    pacer = HostPacer(DEFAULT_HOST_INTERVALS, monotonic=lambda: now[0], sleep=sleep)
    await pacer.wait("https://api.adsb.lol/v2/ladd")
    await pacer.wait("https://API.adsb.lol/v2/pia")
    await pacer.wait("https://www.reddit.com/r/x/new/.rss")
    now[0] += 5
    await pacer.wait("https://api.adsb.lol/v2/mil")
    assert slept == [1.0]
    with pytest.raises(ValueError):
        HostPacer({"api.adsb.lol": 0})


async def test_client_consults_the_pacer_with_the_named_host() -> None:
    seen: list[str] = []

    class RecordingPacer(HostPacer):
        async def wait(self, url: str) -> None:
            seen.append(url)

    client = FeedHttpClient(
        "test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))),
        host_pacer=RecordingPacer({}),
    )
    try:
        await client.get_bytes(URL)
    finally:
        await client.aclose()
    assert seen == [URL]

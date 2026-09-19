"""A throttle pauses every connector using that host, including queued requests."""

import asyncio
from datetime import timedelta

import httpx
import pytest

from ase.adapters.feeds.host_pacing import HostPacer
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.http_contracts import FeedRateLimitedError

HOST = "93.184.216.34"
URL = f"https://{HOST}/feed"


async def test_throttle_defers_shared_host_without_sending_or_sleeping():
    now = [100.0]
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(429, headers={"Retry-After": "90"})

    pacer = HostPacer({HOST: 1.0}, monotonic=lambda: now[0])
    client = FeedHttpClient(
        "test",
        host_pacer=pacer,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        with pytest.raises(FeedRateLimitedError):
            await client.get_bytes(URL)
        now[0] += 10
        with pytest.raises(FeedRateLimitedError) as caught:
            await client.get_bytes(f"https://{HOST}/other-connector")
        assert caught.value.retry_after == timedelta(seconds=80)
        assert len(requests) == 1
        now[0] += 80
        with pytest.raises(FeedRateLimitedError):
            await client.get_bytes(URL)
        assert len(requests) == 2
    finally:
        await client.aclose()


async def test_waiting_request_rechecks_throttle_after_its_spacing_sleep():
    now = [100.0]

    async def sleep(seconds):
        now[0] += seconds
        pacer.rate_limited(URL, timedelta(seconds=20))

    pacer = HostPacer({HOST: 1.0}, monotonic=lambda: now[0], sleep=sleep)
    await pacer.wait(URL)
    with pytest.raises(FeedRateLimitedError) as caught:
        await pacer.wait(URL)
    assert caught.value.retry_after == timedelta(seconds=20)


async def test_cooldown_is_bounded_host_specific_and_uses_fallback():
    now = [100.0]
    pacer = HostPacer({HOST: 1.0}, monotonic=lambda: now[0])
    pacer.rate_limited(URL, None)
    with pytest.raises(FeedRateLimitedError) as caught:
        await pacer.wait(URL)
    assert caught.value.retry_after == timedelta(seconds=60)
    pacer.rate_limited(URL, timedelta(days=1))
    pacer.rate_limited(URL, timedelta(seconds=2))
    with pytest.raises(FeedRateLimitedError) as caught:
        await pacer.wait(URL)
    assert caught.value.retry_after == timedelta(hours=1)
    for index in range(100):
        other = f"https://unconfigured-{index}.invalid/feed"
        pacer.rate_limited(other, None)
        await pacer.wait(other)
    assert len(pacer._cooldowns) == 1


async def test_all_queued_requests_observe_a_throttle_during_spacing():
    now = [100.0]
    sleeping, release = asyncio.Event(), asyncio.Event()

    async def sleep(seconds):
        sleeping.set()
        await release.wait()
        now[0] += seconds

    pacer = HostPacer({HOST: 1.0}, monotonic=lambda: now[0], sleep=sleep)
    await pacer.wait(URL)
    queued = [asyncio.create_task(pacer.wait(URL)) for _ in range(3)]
    await sleeping.wait()
    pacer.rate_limited(URL, timedelta(seconds=30))
    release.set()
    outcomes = await asyncio.gather(*queued, return_exceptions=True)
    assert all(isinstance(outcome, FeedRateLimitedError) for outcome in outcomes)
    assert all(outcome.retry_after == timedelta(seconds=29) for outcome in outcomes)

"""Short-lived tokens, coalesced refreshes and budgets surviving failures/cancellation."""

import asyncio

import httpx
import pytest

from ase.adapters.feeds.barentswatch_tokens import BarentsWatchTokens
from ase.adapters.feeds.http import FeedFetchError
from barentswatch_helpers import (
    ACCESS_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
    monotonic_clock,
    token,
    transport,
)


async def test_concurrent_requests_share_one_token_and_refresh_before_expiry(monkeypatch):
    current = monotonic_clock(monkeypatch)
    requests = []

    async def handle(request):
        requests.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json=token(access_token=f"synthetic-{len(requests)}"))

    http = transport(monkeypatch, handle)
    cache = BarentsWatchTokens(http, CLIENT_ID, CLIENT_SECRET)
    try:
        credentials = await asyncio.gather(*(cache.credential() for _ in range(8)))
        assert len(requests) == 1 and all(c is credentials[0] for c in credentials)
        current[0] += 3569
        assert await cache.credential() is credentials[0]
        current[0] += 1
        fresh = await cache.credential()
        assert fresh is not credentials[0] and len(requests) == 2
        cache.invalidate(credentials[0])
        assert await cache.credential() is fresh
    finally:
        await http.aclose()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        token(access_token=None),
        token(access_token=""),
        token(access_token="x" * 8186),
        token(access_token="x\r\nInjected: evil"),
        token(access_token="x ü"),
        token(expires_in=True),
        token(expires_in="3600"),
        token(expires_in=0),
        token(expires_in=59),
        token(expires_in=86401),
        token(token_type=None),
        token(token_type="Basic"),
        token(scope="api"),
        token(scope="ais api"),
    ],
)
async def test_invalid_tokens_never_enter_cache_or_escape_in_error(monkeypatch, payload):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=payload)

    http = transport(monkeypatch, handle)
    cache = BarentsWatchTokens(http, CLIENT_ID, CLIENT_SECRET)
    try:
        for _ in range(2):
            with pytest.raises(FeedFetchError, match="authentication unavailable") as error:
                await cache.credential()
            assert ACCESS_TOKEN not in str(error.value)
        assert len(calls) == 1 and cache._credential is None
    finally:
        await http.aclose()


async def test_failed_expired_refresh_drops_old_token_and_cools_down(monkeypatch):
    current = monotonic_clock(monkeypatch)
    calls = []

    def handle(request):
        calls.append(request)
        return (
            httpx.Response(200, json=token(expires_in=120))
            if len(calls) == 1
            else httpx.Response(503)
        )

    http = transport(monkeypatch, handle)
    cache = BarentsWatchTokens(http, CLIENT_ID, CLIENT_SECRET)
    try:
        await cache.credential()
        current[0] += 120
        for _ in range(2):
            with pytest.raises(FeedFetchError):
                await cache.credential()
        assert len(calls) == 2 and cache._credential is None
        current[0] += 120
        with pytest.raises(FeedFetchError):
            await cache.credential()
        assert len(calls) == 3
    finally:
        await http.aclose()


async def test_cancelled_refresh_propagates_and_keeps_cooldown(monkeypatch):
    entered = asyncio.Event()
    calls = []

    async def handle(request):
        calls.append(request)
        entered.set()
        await asyncio.Event().wait()

    http = transport(monkeypatch, handle)
    cache = BarentsWatchTokens(http, CLIENT_ID, CLIENT_SECRET)
    task = asyncio.create_task(cache.credential())
    try:
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(FeedFetchError):
            await cache.credential()
        assert len(calls) == 1 and cache._credential is None
    finally:
        await http.aclose()

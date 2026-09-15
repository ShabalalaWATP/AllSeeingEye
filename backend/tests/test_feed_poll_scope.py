"""Conditional validators land only when a whole scheduler poll is published."""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import timedelta
from typing import Any

import httpx
import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.adapters.feeds.mastodon import MastodonConnector
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import CircuitBreaker, HealthRegistry
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.poll_scope import active_poll_scope, poll_scope
from ase.application.feeds.scheduler import FeedScheduler
from feeds_helpers import NOW, FakeClock

BASE = "https://social.test/api/v1/timelines/tag/"


@pytest.fixture(autouse=True)
def no_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    async def allow(url: str) -> None:
        return None

    monkeypatch.setattr(feed_http, "assert_public_host", allow)


def status(key: str) -> dict[str, Any]:
    return {
        "id": key,
        "content": f"<p>Post {key} about the situation on the ground today</p>",
        "url": f"https://social.test/@someone/{key}",
        "created_at": "2026-09-05T00:00:00Z",
    }


def scheduler_for(
    connector: MastodonConnector, timeout: timedelta = timedelta(seconds=5)
) -> FeedScheduler:
    return FeedScheduler(
        [connector],
        Pipeline([Normaliser()]),
        InMemoryEventStore(),
        InMemoryEventBus(),
        HealthRegistry(breaker=CircuitBreaker(disable_after=5)),
        FakeClock(NOW),
        fetch_timeout=timeout,
        jitter=0.0,
    )


def client(handler: Any) -> FeedHttpClient:
    transport = httpx.MockTransport(handler)
    return FeedHttpClient("test-agent", client=httpx.AsyncClient(transport=transport))


async def test_failed_poll_does_not_keep_validators_for_earlier_urls() -> None:
    calls: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        tag = request.url.path.rsplit("/", 1)[-1]
        calls[tag] += 1
        if tag == "one":
            if request.headers.get("if-none-match") == '"v1"':
                return httpx.Response(304)
            return httpx.Response(200, json=[status("a")], headers={"ETag": '"v1"'})
        if calls[tag] == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=[status("b")])

    http = client(handler)
    connector = MastodonConnector(http, FakeClock(NOW), "social.test", ["one", "two"])
    scheduler = scheduler_for(connector)
    try:
        assert not (await scheduler.poll_once(connector)).ok
        second = await scheduler.poll_once(connector)
        # Before the fix, tag one answered 304 here and post "a" was never published.
        assert second.ok and second.fetched == 2
        # After a published poll, the validator is committed and used.
        with pytest.raises(NotModified):
            await http.get_json(f"{BASE}one?limit=40")
    finally:
        await http.aclose()


async def test_timed_out_poll_discards_staged_validators() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/two"):
            await asyncio.sleep(5)
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, json=[status("a")], headers={"ETag": '"v1"'})

    http = client(handler)
    connector = MastodonConnector(http, FakeClock(NOW), "social.test", ["one", "two"])
    try:
        outcome = await scheduler_for(connector, timedelta(milliseconds=50)).poll_once(connector)
        assert not outcome.ok
        assert http._validators == {}
        assert active_poll_scope() is None
    finally:
        await http.aclose()


async def test_scope_commits_explicitly_and_direct_calls_store_immediately() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={}, headers={"ETag": '"v9"'})

    http = client(handler)
    try:
        with poll_scope():
            await http.get_json("https://feeds.test/discarded")
        assert http._validators == {}
        with poll_scope() as scope:
            await http.get_json("https://feeds.test/kept")
            assert http._validators == {}
            scope.commit()
        assert list(http._validators) == ["https://feeds.test/kept"]
        await http.get_json("https://feeds.test/direct")
        assert "https://feeds.test/direct" in http._validators
    finally:
        await http.aclose()

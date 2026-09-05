"""Dynamic RSS URLs cannot grow conditional state without bound or bypass feed safeguards."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.google_news import GoogleNewsWatchlistConnector
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from feeds_helpers import NOW, FakeClock
from watchlists_helpers import RSS, MutablePlans, plan


async def test_dynamic_validator_cache_evicts_old_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    async def allow(url: str) -> None:
        return None

    monkeypatch.setattr(feed_http, "assert_public_host", allow)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"ok", headers={"ETag": '"version1"'})

    client = FeedHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    for index in range(feed_http.MAX_VALIDATORS + 1):
        await client.get_bytes(f"https://example.com/{index}")
    await client.get_bytes(f"https://example.com/{feed_http.MAX_VALIDATORS}")
    assert seen[-1].headers["if-none-match"] == '"version1"'
    await client.get_bytes("https://example.com/0")
    assert "if-none-match" not in seen[-1].headers
    await client.aclose()


async def test_watchlist_uses_guarded_pinned_http_and_bounded_xml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def dns(*_: Any, **__: Any) -> list[tuple[Any, ...]]:
        return [(None, None, None, None, ("93.184.216.34", 0))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", dns)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=RSS)

    client = FeedHttpClient(
        "test", max_bytes=10, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    connector = GoogleNewsWatchlistConnector(client, FakeClock(NOW), MutablePlans([plan("one")]))
    with pytest.raises(FeedFetchError, match="request failed"):
        await connector.fetch()
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "news.google.com"
    assert seen[0].extensions["sni_hostname"] == "news.google.com"
    await client.aclose()


async def test_watchlist_blocks_private_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    async def guard(url: str) -> str:
        if "127.0.0.1" in url:
            raise FeedFetchError("Private address")
        return "93.184.216.34"

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

    client = FeedHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    connector = GoogleNewsWatchlistConnector(client, FakeClock(NOW), MutablePlans([plan("one")]))
    with pytest.raises(FeedFetchError, match="request failed"):
        await connector.fetch()
    assert len(seen) == 1
    await client.aclose()

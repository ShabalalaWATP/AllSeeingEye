"""Outbound HTTP: SSRF guard, size caps, redirects and conditional requests."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import (
    FeedFetchError,
    FeedHttpClient,
    NotModified,
    assert_public_host,
    is_public_address,
)


@pytest.mark.parametrize(
    ("host", "public"),
    [
        ("8.8.8.8", True),
        ("127.0.0.1", False),
        ("10.1.2.3", False),
        ("169.254.169.254", False),
        ("::1", False),
        ("0.0.0.0", False),  # noqa: S104
        ("example.com", True),
    ],
)
def test_is_public_address(host: str, public: bool) -> None:
    assert is_public_address(host) is public


async def test_assert_public_host_rejects_bad_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(FeedFetchError):
        await assert_public_host("ftp://example.com/x")
    with pytest.raises(FeedFetchError):
        await assert_public_host("https://user:pw@example.com/x")
    with pytest.raises(FeedFetchError):
        await assert_public_host("http://127.0.0.1/admin")

    async def resolves_private(*_: Any, **__: Any) -> list[tuple[Any, ...]]:
        return [(None, None, None, None, ("10.0.0.5", 0))]

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", resolves_private)
    with pytest.raises(FeedFetchError, match="non-public"):
        await assert_public_host("https://internal.example.com/feed")

    async def resolves_public(*_: Any, **__: Any) -> list[tuple[Any, ...]]:
        return [(None, None, None, None, ("93.184.216.34", 0))]

    monkeypatch.setattr(loop, "getaddrinfo", resolves_public)
    await assert_public_host("https://example.com/feed")

    async def cannot_resolve(*_: Any, **__: Any) -> list[tuple[Any, ...]]:
        raise socket.gaierror("nope")

    monkeypatch.setattr(loop, "getaddrinfo", cannot_resolve)
    with pytest.raises(FeedFetchError, match="resolve"):
        await assert_public_host("https://missing.example.com/feed")


@pytest.fixture
def no_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    async def allow(url: str) -> None:
        return None

    monkeypatch.setattr(feed_http, "assert_public_host", allow)


def make_client(handler: Any, max_bytes: int = 1_000_000) -> FeedHttpClient:
    transport = httpx.MockTransport(handler)
    return FeedHttpClient(
        "test-agent",
        max_bytes=max_bytes,
        client=httpx.AsyncClient(transport=transport, follow_redirects=False),
    )


async def test_get_json_and_conditional_requests(no_dns: None) -> None:
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.headers))
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, json={"ok": True}, headers={"ETag": '"v1"'})

    client = make_client(handler)
    assert await client.get_json("https://feeds.test/a.json") == {"ok": True}
    with pytest.raises(NotModified):
        await client.get_json("https://feeds.test/a.json")
    assert seen[1]["if-none-match"] == '"v1"'
    assert seen[0]["user-agent"] == "test-agent"
    assert await client.get_text("https://feeds.test/a.json", conditional=False) == '{"ok":true}'
    await client.aclose()


async def chunked_body() -> AsyncIterator[bytes]:
    for _ in range(7):
        yield b"y" * 800


async def test_redirects_errors_and_size_caps(no_dns: None) -> None:
    responses = {
        "/moved": lambda: httpx.Response(302, headers={"Location": "/final"}),
        "/final": lambda: httpx.Response(200, json=[1, 2, 3]),
        "/loop": lambda: httpx.Response(302, headers={"Location": "/loop"}),
        "/no-location": lambda: httpx.Response(302),
        "/big-declared": lambda: httpx.Response(
            200, content=b"x" * 10, headers={"Content-Length": "999999"}
        ),
        # An async iterator body is sent chunked, without a Content-Length to check up front.
        "/big-stream": lambda: httpx.Response(200, content=chunked_body()),
        "/bad-json": lambda: httpx.Response(200, content=b"{not json"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        factory = responses.get(request.url.path)
        return factory() if factory else httpx.Response(503)

    client = make_client(handler, max_bytes=1000)
    assert await client.get_json("https://feeds.test/moved") == [1, 2, 3]
    with pytest.raises(FeedFetchError, match="redirects"):
        await client.get_json("https://feeds.test/loop")
    with pytest.raises(FeedFetchError, match="location"):
        await client.get_json("https://feeds.test/no-location")
    with pytest.raises(FeedFetchError, match="too large"):
        await client.get_json("https://feeds.test/big-declared")
    with pytest.raises(FeedFetchError, match="exceeded"):
        await client.get_json("https://feeds.test/big-stream")
    with pytest.raises(FeedFetchError, match="Invalid JSON"):
        await client.get_json("https://feeds.test/bad-json")
    with pytest.raises(FeedFetchError, match="HTTP 503"):
        await client.get_json("https://feeds.test/down")
    await client.aclose()


async def test_transport_errors_are_wrapped(no_dns: None) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = make_client(handler)
    with pytest.raises(FeedFetchError, match="ConnectError"):
        await client.get_bytes("https://feeds.test/x")
    await client.aclose()

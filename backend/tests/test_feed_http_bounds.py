"""Reject content encodings before decoding and revalidate every redirect."""

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient


class ObservedBody(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.consumed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        self.consumed = True
        yield b"{}"


class SlowBody(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        while True:
            yield b"x"
            await asyncio.sleep(0.02)


async def test_total_deadline_stops_a_slow_drip() -> None:
    client = FeedHttpClient(
        "test",
        total_timeout_seconds=0.08,
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=SlowBody()))
        ),
    )
    try:
        with pytest.raises(FeedFetchError, match="total time limit"):
            await client.get_bytes("https://93.184.216.34/feed")
    finally:
        await client.aclose()


@pytest.mark.parametrize("encoding", ["deflate", "br", "zstd", "gzip, identity", "unknown"])
async def test_rejects_encoding_before_consuming_body(encoding: str) -> None:
    body = ObservedBody()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, headers={"Content-Encoding": encoding}, stream=body)

    client = FeedHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError, match="encoding"):
            await client.get_json("https://93.184.216.34/feed")
        assert not body.consumed
    finally:
        await client.aclose()


async def test_explicit_identity_response_is_supported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Encoding": "identity"}, stream=ObservedBody())

    client = FeedHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        assert await client.get_json("https://93.184.216.34/feed") == {}
    finally:
        await client.aclose()


async def test_injected_client_cannot_follow_redirect_to_private_address() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})

    client = FeedHttpClient(
        "test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True),
    )
    try:
        with pytest.raises(FeedFetchError, match="non-public"):
            await client.get_bytes("https://93.184.216.34/feed")
        assert seen == ["93.184.216.34"]
    finally:
        await client.aclose()


async def test_deep_json_fails_as_a_feed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def parser_depth_failure(_: bytes) -> None:
        raise RecursionError("upstream content must not escape")

    monkeypatch.setattr(feed_http.json, "loads", parser_depth_failure)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[" * 2_000 + b"0" + b"]" * 2_000)

    client = FeedHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError, match="Invalid JSON"):
            await client.get_json("https://93.184.216.34/feed")
    finally:
        await client.aclose()

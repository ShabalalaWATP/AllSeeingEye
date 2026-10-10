"""Fail-closed transport configuration and concurrent address-pin preservation."""

import asyncio

import httpcore
import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.pinned_transport import ORIGINAL_HOST, OriginPinnedTransport
from ase.adapters.geo.camera_http import CameraHttpClient

RESPONSE = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"


class RecordingBackend(httpcore.AsyncMockBackend):
    def __init__(self):
        super().__init__([RESPONSE])
        self.destinations = []

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.destinations.append((host, port))
        await asyncio.sleep(0)
        return await super().connect_tcp(host, port, timeout, local_address, socket_options)


async def test_concurrent_requests_connect_only_to_their_checked_addresses(monkeypatch):
    async def resolve(url):
        return "8.8.8.8" if "one.example" in url else "9.9.9.9"

    monkeypatch.setattr(feed_http, "assert_public_host", resolve)
    backend = RecordingBackend()
    transport = httpx.AsyncHTTPTransport()
    transport._pool._network_backend = backend
    client = FeedHttpClient("test", client=httpx.AsyncClient(transport=transport, trust_env=False))
    try:
        assert await asyncio.gather(
            client.get_bytes("https://one.example:8443/a"),
            client.get_bytes("http://two.example:8080/b"),
        ) == [b"ok", b"ok"]
        assert sorted(backend.destinations) == [("8.8.8.8", 8443), ("9.9.9.9", 8080)]
    finally:
        await client.aclose()


@pytest.mark.parametrize("kind", ["proxy", "unix", "custom"])
async def test_unsupported_network_transport_cannot_bypass_pinning(kind):
    transport = (
        httpx.AsyncHTTPTransport(proxy="http://127.0.0.1:1")
        if kind == "proxy"
        else httpx.AsyncHTTPTransport(uds="not-a-real-socket")
        if kind == "unix"
        else httpx.AsyncBaseTransport()
    )
    client = FeedHttpClient("test", client=httpx.AsyncClient(transport=transport, trust_env=False))
    try:
        with pytest.raises(FeedFetchError):
            await client.get_bytes("https://8.8.8.8/data")
    finally:
        await client.aclose()


async def test_injected_mounts_cannot_bypass_transport_admission():
    raw = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"ok")),
        mounts={"https://8.8.8.8": httpx.AsyncHTTPTransport(proxy="http://127.0.0.1:1")},
        trust_env=False,
    )
    client = FeedHttpClient("test", client=raw)
    try:
        with pytest.raises(FeedFetchError):
            await client.get_bytes("https://8.8.8.8/data")
    finally:
        await client.aclose()


@pytest.mark.parametrize("kind", ["cookie-jar", "cookie-header"])
def test_preloaded_cookies_are_rejected_explicitly(kind):
    raw = httpx.AsyncClient(
        cookies={"private": "synthetic"} if kind == "cookie-jar" else None,
        headers={"Cookie": "private=synthetic"} if kind == "cookie-header" else None,
        transport=httpx.MockTransport(lambda _: httpx.Response(200)),
    )
    with pytest.raises(ValueError, match="must not carry cookies"):
        FeedHttpClient("test", client=raw)


async def test_camera_post_uses_the_same_cookie_boundary():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={}, headers={"Set-Cookie": "private=synthetic; Path=/"})

    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        await client.post_json("https://8.8.8.8/data", {})
        await client.post_json("https://8.8.8.8/data", {})
        assert all("cookie" not in request.headers for request in seen)
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "url,extensions",
    [("https://unchecked.example/a", {}), ("https://8.8.8.8/a", {ORIGINAL_HOST: 123})],
)
async def test_native_transport_refuses_missing_pin_or_invalid_origin(url, extensions):
    transport = OriginPinnedTransport(httpx.AsyncHTTPTransport())
    try:
        with pytest.raises(httpx.ConnectError):
            await transport.handle_async_request(httpx.Request("GET", url, extensions=extensions))
    finally:
        await transport.aclose()

"""Real TLS and CookieJar regressions for IP-pinned shared feed transports."""

import asyncio

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient
from feed_tls_helpers import feed_tls_server


@pytest.fixture
def pinned_loopback(monkeypatch):
    async def checked(_url):
        # Model two public authorities sharing one checked IP, without public traffic.
        return "127.0.0.1"

    monkeypatch.setattr(feed_http, "assert_public_host", checked)


@pytest.mark.parametrize("injected", [False, True])
async def test_pooled_connection_cannot_skip_second_host_verification(
    tmp_path, pinned_loopback, monkeypatch, injected
):
    async with feed_tls_server(tmp_path) as server:
        monkeypatch.setattr(feed_http, "verified_ssl_context", lambda: server.trust)
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
            monkeypatch.delenv(name, raising=False)
            monkeypatch.delenv(name.lower(), raising=False)
        pooled = (
            FeedHttpClient("test", client=httpx.AsyncClient(verify=server.trust, trust_env=False))
            if injected
            else FeedHttpClient("test")
        )
        fresh = FeedHttpClient(
            "test", client=httpx.AsyncClient(verify=server.trust, trust_env=False)
        )
        provider = server.origin("provider.example")
        credential = FeedCredential(provider, "Bearer synthetic-test-only")
        try:
            assert await pooled.get_bytes(server.origin() + "/warm") == b"ok"
            assert await pooled.get_bytes(server.origin() + "/reuse") == b"ok"
            assert server.connections == 1
            for client in (pooled, fresh):
                with pytest.raises(FeedFetchError):
                    await client.get_bytes(provider + "/private", credential=credential)
            assert len(server.requests) == 2
            assert all(b"Authorization:" not in request for request in server.requests)
        finally:
            await pooled.aclose()
            await fresh.aclose()


@pytest.mark.parametrize(
    "cookie", ["isolation=synthetic; Path=/", "isolation=synthetic; Domain=127.0.0.1; Path=/"]
)
async def test_response_cookies_never_cross_or_persist_between_requests(
    tmp_path, pinned_loopback, cookie
):
    async with feed_tls_server(
        tmp_path, names=("source.example", "other.example"), cookie=cookie
    ) as server:
        client = FeedHttpClient(
            "test", client=httpx.AsyncClient(verify=server.trust, trust_env=False)
        )
        try:
            for host in ("source.example", "other.example", "source.example"):
                assert await client.get_bytes(server.origin(host) + "/data") == b"ok"
            assert server.connections == 2
            assert all(b"Cookie:" not in request for request in server.requests)
            assert not client._client.cookies
        finally:
            await client.aclose()


async def test_cancelled_response_releases_connection_and_shutdown_is_repeatable(
    tmp_path, pinned_loopback
):
    async with feed_tls_server(tmp_path) as server:
        client = FeedHttpClient(
            "test", client=httpx.AsyncClient(verify=server.trust, trust_env=False)
        )
        try:
            task = asyncio.create_task(client.get_bytes(server.origin() + "/wait"))
            await asyncio.wait_for(server.waiting.wait(), 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await client.get_bytes(server.origin() + "/after-cancellation") == b"ok"
            assert server.connections == 2
        finally:
            await client.aclose()
            await client.aclose()
        assert client._client.is_closed


async def test_connection_limit_remains_shared_across_original_hosts(tmp_path, pinned_loopback):
    async with feed_tls_server(tmp_path, names=("source.example", "other.example")) as server:
        client = FeedHttpClient(
            "test",
            client=httpx.AsyncClient(
                verify=server.trust,
                trust_env=False,
                limits=httpx.Limits(max_connections=1),
                timeout=httpx.Timeout(5, pool=0.05),
            ),
        )
        task = asyncio.create_task(client.get_bytes(server.origin() + "/wait"))
        try:
            await asyncio.wait_for(server.waiting.wait(), 5)
            with pytest.raises(FeedFetchError):
                await client.get_bytes(server.origin("other.example") + "/blocked")
            assert len(server.requests) == 1
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await client.aclose()

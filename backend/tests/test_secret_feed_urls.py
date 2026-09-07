"""Path-key transport diagnostics, redirects, isolation and failure boundaries."""

import asyncio
import logging
import traceback

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.secret_urls import HTTP_LOGGERS, SecretFeedUrl

KEY = "sentinel_path_key_12345"
TARGET = SecretFeedUrl("https://example.test", f"https://example.test/{KEY}")


@pytest.fixture(autouse=True)
def public_host(monkeypatch):
    async def resolve(url):
        return None

    monkeypatch.setattr(feed_http, "assert_public_host", resolve)


@pytest.mark.parametrize("status", [200, 302, 304, 401, 500])
async def test_no_key_in_logs_errors_cache_or_redirects(caplog, status):
    caplog.set_level(logging.DEBUG)
    calls = []

    def respond(request):
        calls.append(request)
        for name in HTTP_LOGGERS:
            logging.getLogger(name).debug("request %s", request.url)
        return httpx.Response(status, content=b"a", headers={"location": "https://evil.test/"})

    client = FeedHttpClient(
        "tests", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        if status == 200:
            assert await client.get_secret_bytes(TARGET) == b"a"
        else:
            with pytest.raises(FeedFetchError) as error:
                await client.get_secret_bytes(TARGET)
            assert KEY not in "".join(traceback.format_exception(error.value))
        assert len(calls) == 1
        assert client._validators == {}
        assert KEY not in caplog.text
    finally:
        await client.aclose()


@pytest.mark.parametrize("failure", ["dns", "http", "oversize", "encoding"])
async def test_safe_failures(monkeypatch, failure, caplog):
    caplog.set_level(logging.DEBUG)

    async def resolve(url):
        raise FeedFetchError(url)

    if failure == "dns":
        monkeypatch.setattr(feed_http, "assert_public_host", resolve)

    def respond(request):
        if failure == "http":
            raise httpx.ConnectError(str(request.url))
        return httpx.Response(
            200,
            content=b"long",
            headers=({"content-encoding": "unsupported"} if failure == "encoding" else {}),
        )

    client = FeedHttpClient(
        "tests", max_bytes=1, client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        with pytest.raises(FeedFetchError) as error:
            await client.get_secret_bytes(TARGET)
        assert KEY not in "".join(traceback.format_exception(error.value)) + caplog.text
    finally:
        await client.aclose()


async def test_concurrent_public_logging_and_cancellation_restore_context(caplog):
    caplog.set_level(logging.DEBUG)
    entered, release = asyncio.Event(), asyncio.Event()

    async def respond(request):
        if KEY in str(request.url):
            entered.set()
            await release.wait()
        return httpx.Response(200, content=b"ok")

    client = FeedHttpClient(
        "tests", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    task = asyncio.create_task(client.get_secret_bytes(TARGET))
    try:
        await entered.wait()
        await client.get_bytes("https://example.test/public")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        logging.getLogger("httpx").info("after cancellation")
        assert "public" in caplog.text and "after cancellation" in caplog.text
        assert KEY not in caplog.text
    finally:
        release.set()
        task.cancel()
        await client.aclose()


@pytest.mark.parametrize(
    "origin,url",
    [
        ("http://example.test", "http://example.test/x"),
        ("https://example.test", "https://evil.test/x"),
        ("https://example.test", "https://example.test:444/x"),
        ("https://example.test", "https://example.test:0/x"),
        ("https://example.test/x", "https://example.test/x"),
        ("https://example.test", "https://u:p@example.test/x"),
        ("https://example.test", "https://example.test/x\n"),
    ],
)
def test_invalid_secret_origin(origin, url):
    with pytest.raises(ValueError):
        SecretFeedUrl(origin, url)

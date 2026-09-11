"""Guarded OAuth wire format and credential boundaries against synthetic transports."""

import asyncio
import logging
from urllib.parse import parse_qs

import httpx
import pytest
from pydantic import SecretStr

from ase.adapters.feeds import barentswatch_http
from ase.adapters.feeds.barentswatch_http import (
    LATEST_URL,
    TOKEN_URL,
    BarentsWatchHttpClient,
)
from ase.adapters.feeds.barentswatch_tokens import BarentsWatchTokens
from ase.adapters.feeds.http import FeedFetchError
from barentswatch_helpers import ACCESS_TOKEN, CLIENT_ID, CLIENT_SECRET, token, transport


async def test_oauth_form_and_origin_bound_get_are_dns_pinned(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=token() if request.method == "POST" else [])

    http = transport(monkeypatch, handle)
    tokens = BarentsWatchTokens(http, CLIENT_ID, CLIENT_SECRET)
    try:
        credential = await tokens.credential()
        assert await http.get_json(LATEST_URL, credential=credential) == []
        post, get = requests
        assert post.method == "POST" and post.url.path == "/connect/token"
        assert post.url.query == b"" and post.url.host == "8.8.8.8"
        assert post.headers["host"] == "id.barentswatch.no"
        assert post.extensions["sni_hostname"] == "id.barentswatch.no"
        assert post.headers["content-type"] == "application/x-www-form-urlencoded"
        assert parse_qs(post.content.decode()) == {
            "client_id": [CLIENT_ID.get_secret_value()],
            "client_secret": [CLIENT_SECRET.get_secret_value()],
            "scope": ["ais"],
            "grant_type": ["client_credentials"],
        }
        assert "authorization" not in post.headers
        assert get.url.host == "8.8.8.8" and get.url.path == "/v1/latest/combined"
        assert get.headers["host"] == "live.ais.barentswatch.no"
        assert get.extensions["sni_hostname"] == "live.ais.barentswatch.no"
        assert get.headers["authorization"] == f"Bearer {ACCESS_TOKEN}"
        assert "authorization" not in http._client.headers
        assert http._validators == {}
        assert ACCESS_TOKEN not in repr(credential)
    finally:
        await http.aclose()


@pytest.mark.parametrize("destination", ["http://live.ais.barentswatch.no", "https://evil.test"])
async def test_cached_bearer_cannot_be_sent_to_another_origin(monkeypatch, destination):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=token())

    http = transport(monkeypatch, handle)
    try:
        credential = await BarentsWatchTokens(http, CLIENT_ID, CLIENT_SECRET).credential()
        with pytest.raises(FeedFetchError, match="origin"):
            await http.get_json(destination, credential=credential)
        assert len(calls) == 1
    finally:
        await http.aclose()


@pytest.mark.parametrize("value", ["", " ", "x" * 2049, "x\n", "x\x7f"])
async def test_invalid_configuration_never_reaches_dns_or_transport(monkeypatch, value):
    http = transport(monkeypatch, lambda _: pytest.fail("No request expected"))
    try:
        with pytest.raises(FeedFetchError, match="authentication failed"):
            await http.token(SecretStr(value), CLIENT_SECRET)
    finally:
        await http.aclose()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 403, 429, 500])
async def test_post_never_follows_redirects_or_retries_status_errors(monkeypatch, status):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(status, text="secret echoed response", headers={"location": "/evil"})

    http = transport(monkeypatch, handle)
    try:
        with pytest.raises(FeedFetchError) as error:
            await http.token(CLIENT_ID, CLIENT_SECRET)
        assert len(requests) == 1 and "secret" not in str(error.value)
        assert error.value.__suppress_context__
    finally:
        await http.aclose()


@pytest.mark.parametrize("mode", ["compression", "declared", "chunks", "json", "transport"])
async def test_token_response_limits_and_safe_diagnostics(monkeypatch, caplog, mode):
    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * 8
            yield b"x" * 8

    def handle(request):
        logging.getLogger("httpx").warning("secret %s", CLIENT_SECRET.get_secret_value())
        logging.getLogger("httpcore.http11").warning("secret body")
        if mode == "transport":
            raise httpx.ConnectError(CLIENT_SECRET.get_secret_value())
        headers = {
            "compression": {"content-encoding": "gzip"},
            "declared": {"content-length": "999999"},
        }.get(mode, {})
        return httpx.Response(200, headers=headers, stream=Chunks())

    monkeypatch.setattr(barentswatch_http, "TOKEN_MAX_BYTES", 12 if mode == "chunks" else 100)
    caplog.set_level(logging.DEBUG)
    http = transport(monkeypatch, handle)
    try:
        with pytest.raises(FeedFetchError) as error:
            await http.token(CLIENT_ID, CLIENT_SECRET)
        assert "secret" not in caplog.text
        assert CLIENT_SECRET.get_secret_value() not in str(error.value)
    finally:
        await http.aclose()


async def test_private_dns_failure_is_sanitised_before_transport(monkeypatch):
    http = transport(monkeypatch, lambda _: pytest.fail("No request expected"))

    async def private(url):
        assert url == TOKEN_URL
        raise FeedFetchError("private destination with secret")

    monkeypatch.setattr(barentswatch_http, "assert_public_host", private)
    try:
        with pytest.raises(FeedFetchError, match="authentication failed"):
            await http.token(CLIENT_ID, CLIENT_SECRET)
    finally:
        await http.aclose()


async def test_token_deadline_includes_dns_and_transport(monkeypatch):
    async def blocked(request):
        await asyncio.Event().wait()

    monkeypatch.setattr(barentswatch_http, "REQUEST_SECONDS", 0.01)
    http = transport(monkeypatch, blocked)
    try:
        with pytest.raises(FeedFetchError, match="authentication failed"):
            await http.token(CLIENT_ID, CLIENT_SECRET)
    finally:
        await http.aclose()


async def test_owned_transport_has_no_environment_proxy_and_closes():
    http = BarentsWatchHttpClient("synthetic-tests")
    assert http._client._trust_env is False
    assert http._max_bytes == 5 * 1024 * 1024
    await http.aclose()
    assert http._client.is_closed

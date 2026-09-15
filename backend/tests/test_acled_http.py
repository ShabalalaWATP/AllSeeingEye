"""ACLED OAuth wire format and bearer reads against synthetic transports, never the network."""

from __future__ import annotations

import logging
from collections.abc import Callable
from urllib.parse import parse_qs

import httpx
import pytest
from pydantic import SecretStr
from structlog.testing import capture_logs

from acled_helpers import CIPHER, ENV_REFRESH, MemoryStore, grant
from ase.adapters.feeds import acled_http
from ase.adapters.feeds.acled_http import (
    TOKEN_URL,
    AcledHttpClient,
    AcledRefreshRejected,
    AcledUnauthorised,
)
from ase.adapters.feeds.acled_tokens import AcledTokens
from ase.adapters.feeds.conflict_acled import SPEC, AcledConnector
from ase.adapters.feeds.http import FeedCredential, FeedFetchError
from feeds_helpers import NOW, FakeClock

READ_URL = SPEC.url + "?page=1"
CREDENTIAL = FeedCredential("https://acleddata.com", "Bearer synthetic-access-0001")


def client(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> AcledHttpClient:
    async def guard(url: str) -> str:
        assert url.startswith("https://acleddata.com/")
        return "8.8.8.8"

    monkeypatch.setattr(acled_http, "assert_public_host", guard)
    return AcledHttpClient(
        "synthetic-tests", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


async def test_refresh_posts_a_dns_pinned_form_without_authorisation(monkeypatch) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=grant(1))

    http = client(monkeypatch, handle)
    try:
        assert await http.refresh(SecretStr(ENV_REFRESH)) == grant(1)
    finally:
        await http.aclose()
    [post] = requests
    assert post.method == "POST" and post.url.path == "/oauth/token" and post.url.query == b""
    assert post.url.host == "8.8.8.8" and post.headers["host"] == "acleddata.com"
    assert post.extensions["sni_hostname"] == "acleddata.com"
    assert post.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(post.content.decode()) == {
        "refresh_token": [ENV_REFRESH],
        "grant_type": ["refresh_token"],
        "client_id": ["acled"],
    }
    assert "authorization" not in post.headers
    assert TOKEN_URL == "https://acleddata.com/oauth/token"


@pytest.mark.parametrize("status", [400, 401])
async def test_refused_refresh_token_is_reported_without_upstream_text(monkeypatch, status) -> None:
    http = client(
        monkeypatch, lambda _: httpx.Response(status, json={"error": "secret-upstream-detail"})
    )
    try:
        with pytest.raises(AcledRefreshRejected) as error:
            await http.refresh(SecretStr(ENV_REFRESH))
    finally:
        await http.aclose()
    assert "secret-upstream-detail" not in str(error.value) and error.value.__cause__ is None


@pytest.mark.parametrize(
    "response",
    [
        lambda: httpx.Response(500, text="secret-upstream-detail"),
        lambda: httpx.Response(200, text="not json secret-upstream-detail"),
        lambda: httpx.Response(200, content=b"x" * (65 * 1024)),
        lambda: httpx.Response(
            200, stream=httpx.ByteStream(b"{}"), headers={"content-encoding": "gzip"}
        ),
    ],
)
async def test_other_token_failures_are_generic(monkeypatch, response) -> None:
    http = client(monkeypatch, lambda _: response())
    try:
        with pytest.raises(FeedFetchError) as error:
            await http.refresh(SecretStr(ENV_REFRESH))
    finally:
        await http.aclose()
    assert not isinstance(error.value, AcledRefreshRejected)
    assert str(error.value) == "ACLED authentication failed."


@pytest.mark.parametrize("value", ["", "has space", "x" * 9000, "tab\there"])
async def test_malformed_refresh_tokens_are_never_sent(monkeypatch, value) -> None:
    calls: list[httpx.Request] = []
    http = client(monkeypatch, lambda request: calls.append(request) or httpx.Response(200))
    try:
        with pytest.raises(AcledRefreshRejected):
            await http.refresh(SecretStr(value))
    finally:
        await http.aclose()
    assert calls == []


async def test_bearer_read_reports_401_and_hides_other_statuses(monkeypatch) -> None:
    statuses = iter([401, 403, 200])

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer synthetic-access-0001"
        assert request.headers["host"] == "acleddata.com"
        status = next(statuses)
        return httpx.Response(status, json={"status": 200, "data": [], "detail": "secret"})

    http = client(monkeypatch, handle)
    try:
        with pytest.raises(AcledUnauthorised):
            await http.read_json(READ_URL, CREDENTIAL)
        with pytest.raises(FeedFetchError) as error:
            await http.read_json(READ_URL, CREDENTIAL)
        assert "secret" not in str(error.value) and not isinstance(error.value, AcledUnauthorised)
        assert (await http.read_json(READ_URL, CREDENTIAL))["status"] == 200
    finally:
        await http.aclose()


async def test_bearer_is_never_sent_to_another_origin(monkeypatch) -> None:
    calls: list[httpx.Request] = []
    http = client(monkeypatch, lambda request: calls.append(request) or httpx.Response(200))
    try:
        with pytest.raises(FeedFetchError):
            await http.read_json("https://evil.test/api", CREDENTIAL)
    finally:
        await http.aclose()
    assert calls == []


async def test_connector_refreshes_after_401_end_to_end_without_logging_secrets(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    grants = iter([grant(1), grant(2)])
    reads = iter([httpx.Response(401), httpx.Response(200, json={"status": 200, "data": []})])

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=next(grants))
        return next(reads)

    http = client(monkeypatch, handle)
    store = MemoryStore()
    tokens = AcledTokens(http, FakeClock(NOW), SecretStr(ENV_REFRESH), store, CIPHER)
    connector = AcledConnector(http, FakeClock(NOW), tokens=tokens)
    try:
        with capture_logs() as logs, caplog.at_level(logging.DEBUG):
            assert await connector.fetch() == []
    finally:
        await tokens.aclose()
    assert store.value is not None
    assert CIPHER.decrypt(store.value.encrypted) == "synthetic-rotated-refresh-0002"
    rendered = repr(logs) + caplog.text
    for secret in (ENV_REFRESH, "synthetic-access", "synthetic-rotated-refresh"):
        assert secret not in rendered


def test_connector_requires_a_token_source() -> None:
    with pytest.raises(ValueError, match="refresh token or a current access token"):
        AcledConnector(object(), FakeClock(NOW))  # type: ignore[arg-type]

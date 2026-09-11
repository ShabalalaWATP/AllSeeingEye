"""Optional factory wiring, polling budgets, admission and safe cancellation."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from ase.adapters.feeds import barentswatch
from ase.adapters.feeds.barentswatch import SPEC, BarentsWatchConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.application.ports.feed_diagnostics import FeedDeferred
from ase.container import Container
from barentswatch_helpers import (
    CLIENT_ID,
    CLIENT_SECRET,
    monotonic_clock,
    token,
    transport,
    vessel,
)
from feeds_helpers import NOW, FakeClock, FakeHttp
from test_pipeline_and_scheduler import build_scheduler


async def test_poll_cooldown_caches_token_and_refreshes_stationary_records(monkeypatch):
    current = monotonic_clock(monkeypatch)
    clock = FakeClock(NOW)
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=token() if request.method == "POST" else [vessel(msgtime=clock.now().isoformat())],
        )

    http = transport(monkeypatch, handle)
    connector = BarentsWatchConnector(http, clock, CLIENT_ID, CLIENT_SECRET)
    scheduler, store, _, _ = build_scheduler([], clock)
    try:
        first = await scheduler.poll_once(connector)
        assert first.ok and first.fetched == 1 and store.stats().total == 1
        deferred = await scheduler.poll_once(connector)
        assert not deferred.ok and "cooldown" in deferred.error
        assert len(calls) == 2
        current[0] += 120
        clock.advance(timedelta(seconds=120))
        second = await scheduler.poll_once(connector)
        assert second.ok and second.changed == 1
        assert [call.method for call in calls] == ["POST", "GET", "GET"]
    finally:
        await http.aclose()


@pytest.mark.parametrize(
    "mode", ["authentication", "redirect", "http", "body", "json", "exception"]
)
async def test_failure_never_falls_back_or_retries_or_leaks(monkeypatch, caplog, mode):
    current = monotonic_clock(monkeypatch)
    calls = []

    def handle(request):
        calls.append(request)
        logging.getLogger("httpcore.http11").warning("secret echoed header")
        if request.method == "POST":
            return (
                httpx.Response(401)
                if mode == "authentication"
                else httpx.Response(200, json=token())
            )
        if mode == "exception":
            raise RuntimeError("secret echoed token")
        return httpx.Response(
            {"redirect": 302, "http": 401}.get(mode, 200),
            headers={"location": "https://evil.test", "content-length": "9000000"}
            if mode in {"redirect", "body"}
            else {},
            content=b"secret invalid body",
        )

    caplog.set_level(logging.DEBUG)
    http = transport(monkeypatch, handle)
    connector = BarentsWatchConnector(http, FakeClock(NOW), CLIENT_ID, CLIENT_SECRET)
    try:
        with pytest.raises(FeedFetchError) as error:
            await connector.fetch()
        assert str(error.value) == "BarentsWatch snapshot request failed."
        assert "secret" not in caplog.text
        assert len(calls) == (1 if mode == "authentication" else 2)
        with pytest.raises(FeedDeferred):
            await connector.fetch()
        assert connector._tokens._credential is None
        current[0] += 120
        with pytest.raises(FeedFetchError):
            await connector.fetch()
        assert len(calls) == (2 if mode == "authentication" else 4)
    finally:
        await http.aclose()


@pytest.mark.parametrize("action", ["cancel", "timeout"])
async def test_snapshot_deadline_and_cancellation_keep_poll_budget(monkeypatch, action):
    entered = asyncio.Event()
    calls = []

    async def handle(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(200, json=token())
        entered.set()
        await asyncio.Event().wait()

    if action == "timeout":
        monkeypatch.setattr(barentswatch, "FETCH_SECONDS", 0.01)
    http = transport(monkeypatch, handle)
    connector = BarentsWatchConnector(http, FakeClock(NOW), CLIENT_ID, CLIENT_SECRET)
    task = asyncio.create_task(connector.fetch())
    try:
        await entered.wait()
        if action == "cancel":
            task.cancel()
        with pytest.raises(asyncio.CancelledError if action == "cancel" else FeedFetchError):
            await task
        with pytest.raises(FeedDeferred):
            await connector.fetch()
        assert len(calls) == 2
    finally:
        await http.aclose()


@pytest.mark.parametrize("disable_when", ["before", "during", "enabled"])
async def test_shared_scheduler_admission_blocks_fetch_and_late_publication(
    monkeypatch, disable_when
):
    class Admission:
        allowed = disable_when != "before"

        async def enabled(self, source_id):
            assert source_id == SPEC.id
            return self.allowed

        @asynccontextmanager
        async def guard(self):
            yield

    admission = Admission()
    calls = []

    def handle(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(200, json=token())
        admission.allowed = disable_when != "during"
        return httpx.Response(200, json=[vessel()])

    http = transport(monkeypatch, handle)
    connector = BarentsWatchConnector(http, FakeClock(NOW), CLIENT_ID, CLIENT_SECRET)
    scheduler, store, _, _ = build_scheduler([], FakeClock(NOW))
    scheduler._admission = admission
    try:
        outcome = await scheduler.poll_once(connector)
        assert outcome.ok is (disable_when == "enabled")
        assert store.stats().total == (1 if disable_when == "enabled" else 0)
        assert len(calls) == (0 if disable_when == "before" else 2)
    finally:
        await http.aclose()


@pytest.mark.parametrize(
    ("client_id", "client_secret", "enabled"),
    [
        (None, None, False),
        (None, CLIENT_SECRET, False),
        (CLIENT_ID, None, False),
        (SecretStr(" "), CLIENT_SECRET, False),
        (CLIENT_ID, SecretStr(""), False),
        (CLIENT_ID, CLIENT_SECRET, True),
    ],
)
async def test_factory_requires_both_nonblank_credentials(
    monkeypatch, client_id, client_secret, enabled
):
    http = transport(monkeypatch, lambda _: pytest.fail("Factory must not fetch"))
    try:
        connectors = build_connectors(
            FakeHttp(),
            FakeClock(NOW),
            barentswatch_http=http,
            barentswatch_client_id=client_id,
            barentswatch_client_secret=client_secret,
        )
        assert sum(c.spec.id == SPEC.id for c in connectors) == int(enabled)
        disabled = build_connectors(
            FakeHttp(),
            FakeClock(NOW),
            disabled=[SPEC.id],
            barentswatch_http=http,
            barentswatch_client_id=CLIENT_ID,
            barentswatch_client_secret=CLIENT_SECRET,
        )
        assert all(c.spec.id != SPEC.id for c in disabled)
    finally:
        await http.aclose()


async def test_settings_and_container_wire_protected_credentials_and_dispose(
    settings, clock, email_sender
):
    settings.barentswatch_client_id = CLIENT_ID
    settings.barentswatch_client_secret = CLIENT_SECRET
    assert CLIENT_ID.get_secret_value() not in repr(settings)
    assert CLIENT_SECRET.get_secret_value() not in settings.model_dump_json()
    container = Container(settings, clock=clock, email_sender=email_sender)
    try:
        connector = next(c for c in container.connectors if c.spec.id == SPEC.id)
        assert connector._http is container.barentswatch_http
        assert connector in container.scheduler.connectors
    finally:
        await container.dispose()
    assert container.barentswatch_http._client.is_closed

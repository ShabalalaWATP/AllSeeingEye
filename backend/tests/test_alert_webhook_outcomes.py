"""No external requests: pinning, every-send DNS checks and ambiguous transport outcomes."""

import asyncio
import logging
from uuid import uuid4

import httpx
import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.notify.webhook import WebhookNotifier
from ase.domain.notification_delivery import DeliveryOutcome
from ase.domain.warning import alert_from, evaluate
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


def firing():
    rule = indicator()
    match = evaluate(rule, conflict_events(NOW), NOW, None)
    assert match is not None
    return alert_from(rule, match, uuid4(), NOW), rule


@pytest.mark.parametrize(
    "status,expected", [(204, "sent"), (302, "retryable"), (429, "retryable"), (503, "uncertain")]
)
async def test_pinned_dispatch_preserves_tls_identity_and_does_not_follow_redirects(
    monkeypatch, status, expected
):
    requests = []

    async def public(_url):
        return "8.8.8.8"

    async def handle(request):
        requests.append(request)
        return httpx.Response(status, headers={"Location": "https://127.0.0.1/secret"})

    monkeypatch.setattr("ase.adapters.notify.webhook.assert_public_host", public)
    alert, rule = firing()
    notifier = WebhookNotifier(
        "https://example.com/secret", "test", transport=httpx.MockTransport(handle)
    )
    assert (await notifier.send_outcome(alert, rule)).value == expected
    assert len(requests) == 1
    assert requests[0].url.host == "8.8.8.8"
    assert requests[0].headers["Host"] == "example.com"
    assert requests[0].extensions["sni_hostname"] == "example.com"
    assert requests[0].headers["Idempotency-Key"] == str(alert.id)


async def test_dns_rebinding_is_rechecked_before_each_send(monkeypatch):
    calls = 0
    sent = []

    async def public(_url):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FeedFetchError("Address is not public.")
        return "8.8.8.8"

    async def handle(request):
        sent.append(request)
        return httpx.Response(204)

    monkeypatch.setattr("ase.adapters.notify.webhook.assert_public_host", public)
    notifier = WebhookNotifier(
        "https://example.com/secret", "test", transport=httpx.MockTransport(handle)
    )
    alert, rule = firing()
    assert await notifier.send_outcome(alert, rule) is DeliveryOutcome.SENT
    assert await notifier.send_outcome(alert, rule) is DeliveryOutcome.RETRYABLE
    assert calls == 2 and len(sent) == 1


async def test_lost_response_is_uncertain_and_does_not_log_credentials(monkeypatch, caplog):
    async def public(_url):
        return "8.8.8.8"

    async def handle(_request):
        raise httpx.ReadError("https://example.com/private-token")

    monkeypatch.setattr("ase.adapters.notify.webhook.assert_public_host", public)
    notifier = WebhookNotifier(
        "https://example.com/private-token", "test", transport=httpx.MockTransport(handle)
    )
    alert, rule = firing()
    assert await notifier.send_outcome(alert, rule) is DeliveryOutcome.UNCERTAIN
    assert "private-token" not in caplog.text


@pytest.mark.parametrize("fails", [False, True])
async def test_transport_diagnostics_redact_only_protected_request(monkeypatch, caplog, fails):
    caplog.set_level(logging.DEBUG)
    entered, release = asyncio.Event(), asyncio.Event()

    async def public(_url):
        return "8.8.8.8"

    async def protected(request):
        for name in ("httpcore.connection", "httpcore.http11", "httpcore.http2", "httpcore.proxy"):
            logging.getLogger(name).debug("diagnostic %s", request.url)
        entered.set()
        await release.wait()
        if fails:
            raise httpx.ReadError(str(request.url))
        return httpx.Response(204)

    async def ordinary(_request):
        return httpx.Response(200)

    monkeypatch.setattr("ase.adapters.notify.webhook.assert_public_host", public)
    notifier = WebhookNotifier(
        "https://example.com/path-secret?token=query-secret",
        "test",
        transport=httpx.MockTransport(protected),
    )
    alert, rule = firing()
    sending = asyncio.create_task(notifier.send_outcome(alert, rule))
    await entered.wait()
    async with httpx.AsyncClient(transport=httpx.MockTransport(ordinary)) as client:
        await client.get("https://ordinary.example.com/public-request")
    release.set()
    assert await sending is (DeliveryOutcome.UNCERTAIN if fails else DeliveryOutcome.SENT)
    assert "path-secret" not in caplog.text and "query-secret" not in caplog.text
    assert "ordinary.example.com/public-request" in caplog.text

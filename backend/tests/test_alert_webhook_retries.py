"""A gateway response cannot prove whether the receiver applied a webhook."""

import json
from datetime import timedelta
from functools import partial

import httpx
import pytest

from alert_routing_helpers import destination, fire, outbox, rule, save_route
from ase.adapters.notify.webhook import WebhookNotifier
from ase.container.alert_routing import alert_dispatcher


async def routed_webhook(client, container, user, monkeypatch, handle):
    headers, rule_id = await rule(client, user)
    target = await destination(client, headers, monkeypatch)
    await save_route(client, headers, rule_id, email=False, webhook=target)

    async def public(_url):
        return "8.8.8.8"

    monkeypatch.setattr("ase.adapters.notify.webhook.assert_public_host", public)
    monkeypatch.setattr(
        "ase.adapters.notify.alert_routing.WebhookNotifier",
        partial(WebhookNotifier, transport=httpx.MockTransport(handle)),
    )
    alert = await fire(container, rule_id)
    return alert, alert_dispatcher(container)


@pytest.mark.parametrize("gateway_status", [502, 503, 504])
@pytest.mark.parametrize("receiver_deduplicates", [False, True])
async def test_acceptance_before_gateway_error_can_duplicate_receiver_effects(
    client, container, user, clock, monkeypatch, gateway_status, receiver_deduplicates
):
    requests, applied = [], []

    async def gateway(request):
        key = request.headers["Idempotency-Key"]
        requests.append((key, json.loads(request.content)["id"]))
        # The receiver commits before its gateway supplies the unsuccessful response.
        if not receiver_deduplicates or key not in applied:
            applied.append(key)
        return httpx.Response(gateway_status if len(requests) == 1 else 204)

    alert, dispatcher = await routed_webhook(client, container, user, monkeypatch, gateway)
    assert await dispatcher.tick() == 1
    first = (await outbox(container))[0]
    assert first.state == "pending" and first.attempts == 1
    assert first.next_attempt_at == clock.now() + timedelta(minutes=5)
    assert applied == [str(alert.id)]
    assert await dispatcher.tick() == 0
    clock.advance(timedelta(minutes=5) - timedelta(seconds=1))
    assert await dispatcher.tick() == 0
    clock.advance(timedelta(seconds=1))
    assert await dispatcher.tick() == 1
    final = (await outbox(container))[0]
    assert final.state == "sent" and final.attempts == 2
    assert requests == [(str(alert.id), str(alert.id))] * 2
    assert len(applied) == (1 if receiver_deduplicates else 2)
    assert await dispatcher.tick() == 0


async def test_gateway_errors_exhaust_attempts_even_when_receiver_accepted_every_request(
    client, container, user, clock, monkeypatch
):
    applied = []

    async def gateway(request):
        applied.append(request.headers["Idempotency-Key"])
        return httpx.Response(504)

    alert, dispatcher = await routed_webhook(client, container, user, monkeypatch, gateway)
    for attempt in range(1, 4):
        assert await dispatcher.tick() == 1
        current = (await outbox(container))[0]
        assert current.attempts == attempt
        assert current.state == ("pending" if attempt < 3 else "failed")
        assert current.next_attempt_at == clock.now() + timedelta(minutes=5 * attempt)
        assert await dispatcher.tick() == 0
        clock.advance(timedelta(minutes=5 * attempt))
    assert applied == [str(alert.id)] * 3
    assert await dispatcher.tick() == 0

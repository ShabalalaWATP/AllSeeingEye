"""Committed alert intents survive transport failures and honour current authority and opt-outs."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from alert_routing_helpers import (
    delivery_store,
    destination,
    enable_mail,
    fire,
    outbox,
    rule,
    save_route,
)
from ase.adapters.persistence.alert_notification_enqueue import enqueue_alert_notifications
from ase.adapters.persistence.alert_routing_models import (
    AlertNotificationRow,
    AlertRoutingRow,
    AlertWebhookDestinationRow,
)
from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.application.warning.notification_dispatch import AlertNotificationDispatcher
from ase.container.alert_routing import alert_dispatcher
from ase.domain.alert_routing import AlertDeliveryClaim
from ase.domain.notification_delivery import DeliveryOutcome, EmailPreferences
from tracker_helpers import conflict_events


class Sender:
    def __init__(self, outcomes):
        self.outcomes, self.messages = iter(outcomes), []

    async def send(self, message):
        self.messages.append(message)
        result = next(self.outcomes)
        if isinstance(result, Exception):
            raise result
        return result


async def test_unique_three_channel_intents_and_failure_isolation(
    client, container, user, monkeypatch
):
    headers, rule_id = await rule(client, user)
    target = await destination(client, headers, monkeypatch)
    await enable_mail(container, user)
    await save_route(client, headers, rule_id, webhook=target)
    alert = await fire(container, rule_id, installation=True)
    async with container.session_factory() as session:
        await enqueue_alert_notifications(session, alert, installation_copy=True)
        await session.commit()
    assert {row.channel for row in await outbox(container)} == {
        "email",
        "webhook",
        "installation_webhook",
    }
    sender = Sender(
        [RuntimeError("secret-bearing failure"), DeliveryOutcome.SENT, DeliveryOutcome.SENT]
    )
    dispatcher = AlertNotificationDispatcher(
        delivery_store(container, installation_url="https://example.com/installation"),
        sender,
        container.clock,
    )
    assert await dispatcher.tick() == 3
    assert len(sender.messages) == 3
    assert sorted(row.state for row in await outbox(container)) == ["sent", "sent", "uncertain"]
    assert await dispatcher.tick() == 0
    assert (await client.get("/api/warning/alerts", headers=headers)).json()["items"][0][
        "id"
    ] == str(alert.id)
    email = next(item.email for item in sender.messages if item.email)
    assert email.recipient == user.email and "Private topic" not in email.body


@pytest.mark.parametrize(
    "change", ["optout", "unconfirmed", "account_disabled", "route_changed", "destination_disabled"]
)
async def test_delivery_rechecks_current_state(client, container, user, monkeypatch, change):
    headers, rule_id = await rule(client, user)
    target = await destination(client, headers, monkeypatch)
    await enable_mail(container, user)
    await save_route(
        client,
        headers,
        rule_id,
        webhook=target if change == "destination_disabled" else None,
        email=change != "destination_disabled",
    )
    await fire(container, rule_id)
    store = delivery_store(container)
    claim = await store.claim(container.clock.now())
    assert claim
    async with container.session_factory() as session:
        if change == "optout":
            await SqlNotificationPreferences(session).save_email(
                user.id, EmailPreferences(False, False)
            )
            await SqlNotificationPreferences(session).save_email(
                user.id, EmailPreferences(True, False)
            )
        elif change == "unconfirmed":
            await SqlMfaRepository(session).set_email_enabled(user.id, False)
        elif change == "account_disabled":
            await session.execute(
                update(UserRow).where(UserRow.id == user.id).values(is_active=False)
            )
        elif change == "route_changed":
            await session.execute(update(AlertRoutingRow).values(revision=2))
        else:
            await session.execute(update(AlertWebhookDestinationRow).values(enabled=False))
        await session.commit()
    assert await store.prepare(claim, container.clock.now()) is None


async def test_optout_before_claim_cannot_revive_old_mail(client, container, user):
    headers, rule_id = await rule(client, user)
    await enable_mail(container, user)
    await save_route(client, headers, rule_id)
    await fire(container, rule_id)
    async with container.session_factory() as session:
        preferences = SqlNotificationPreferences(session)
        await preferences.save_email(user.id, EmailPreferences(False, False))
        await preferences.save_email(user.id, EmailPreferences(True, False))
        await session.commit()
    assert await delivery_store(container).claim(container.clock.now()) is None
    assert (await outbox(container))[0].state == "cancelled"


async def test_bounded_attempts_and_interrupted_claims_are_not_retried(
    client, container, user, clock
):
    headers, rule_id = await rule(client, user)
    await enable_mail(container, user)
    await save_route(client, headers, rule_id)
    await fire(container, rule_id)
    sender = Sender([DeliveryOutcome.RETRYABLE] * 3)
    store = delivery_store(container)
    dispatcher = AlertNotificationDispatcher(store, sender, clock)
    for _ in range(3):
        assert await dispatcher.tick() == 1
        clock.advance(timedelta(hours=1))
    assert (await outbox(container))[0].state == "failed"
    assert await dispatcher.tick() == 0
    async with container.session_factory() as session:
        await session.execute(
            update(AlertNotificationRow).values(
                state="sending", updated_at=clock.now() - timedelta(minutes=3)
            )
        )
        await session.commit()
    await store.recover_uncertain(clock.now())
    assert (await outbox(container))[0].state == "uncertain"
    assert await dispatcher.tick() == 0


async def test_no_route_defaults_and_disabled_installation_copy(client, container, user):
    _, rule_id = await rule(client, user)
    await fire(container, rule_id, installation=True)
    store = delivery_store(container)
    claim = await store.claim(container.clock.now())
    assert claim and claim.channel == "installation_webhook"
    assert await store.prepare(claim, container.clock.now()) is None
    assert (await outbox(container))[0].safe_reason == "installation_copy_disabled"


async def test_competing_claims_and_stale_completion_cannot_rewrite_outcome(
    client, container, user
):
    headers, rule_id = await rule(client, user)
    await enable_mail(container, user)
    await save_route(client, headers, rule_id)
    await fire(container, rule_id)
    stores = (delivery_store(container), delivery_store(container))
    claims = await asyncio.gather(*(store.claim(container.clock.now()) for store in stores))
    owned = [claim for claim in claims if claim is not None]
    assert len(owned) == 1
    claim = owned[0]
    stale = AlertDeliveryClaim(
        claim.id, claim.alert_id, claim.channel, claim.destination_ref, uuid4(), claim.attempts
    )
    assert await stores[0].prepare(stale, container.clock.now()) is None
    await stores[0].finish(stale, DeliveryOutcome.SENT, container.clock.now())
    assert (await outbox(container))[0].state == "sending"
    assert await stores[0].prepare(claim, container.clock.now()) is not None
    await stores[0].finish(claim, DeliveryOutcome.SENT, container.clock.now())
    await stores[1].finish(claim, DeliveryOutcome.RETRYABLE, container.clock.now())
    assert (await outbox(container))[0].state == "sent"


async def test_container_sends_installation_copy_once_after_storing_alert(
    client, container, user, monkeypatch
):
    headers, _ = await rule(client, user)
    container.settings.alert_webhook_url = "https://example.com/installation"
    sent = []

    async def send(_notifier, alert, indicator):
        sent.append((alert.id, indicator.name))
        return DeliveryOutcome.SENT

    monkeypatch.setattr("ase.adapters.notify.webhook.WebhookNotifier.send_outcome", send)
    container.store.upsert(conflict_events(container.clock.now()))
    evaluator = container.build_evaluator()
    fired = await evaluator.run_once()
    assert len(fired) == 1 and sent == []
    assert len((await client.get("/api/warning/alerts", headers=headers)).json()["items"]) == 1
    dispatcher = alert_dispatcher(container)
    assert await dispatcher.tick() == 1
    assert sent == [(fired[0].id, "Routing rule")]
    assert await evaluator.run_once() == []
    assert await dispatcher.tick() == 0

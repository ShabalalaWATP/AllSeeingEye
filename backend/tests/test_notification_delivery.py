"""Subscription mail is opt-in, transactionally unique and conservatively retried."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.persistence.notification_delivery import SqlEditionDeliveryStore
from ase.adapters.persistence.notification_enqueue import queue_edition_notifications
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.account.notification_dispatch import NotificationDispatcher
from ase.container import Container
from ase.domain.notification_delivery import (
    DeliveryOutcome,
    EditionEmailPolicy,
    EmailPreferences,
    NotificationEmail,
    SubscriptionEmailPreferences,
)
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.users import User
from helpers import FakeClock
from test_subscription_editions import _edition, _reserve, _revision


class Sender:
    def __init__(self, outcome=DeliveryOutcome.SENT, *, available=True):
        self.outcome, self.available = outcome, available
        self.messages: list[NotificationEmail] = []

    async def send(self, message):
        self.messages.append(message)
        return self.outcome


async def setup_delivery(container, user, policy=EditionEmailPolicy.EVERY, *, attention=True):
    schedule, revision = await _revision(container, user)
    edition = await _reserve(container, _edition(schedule, revision))
    async with container.session_factory() as session:
        preferences = SqlNotificationPreferences(session)
        await SqlMfaRepository(session).set_email_enabled(user.id, True)
        await preferences.save_email(user.id, EmailPreferences(True, False))
        await preferences.save_subscription(
            user.id,
            schedule.id,
            SubscriptionEmailPreferences(policy, attention),
        )
        await session.commit()
    store = SqlEditionDeliveryStore(
        container.session_factory,
        container.access_policy,
        container.settings.public_base_url,
    )
    return schedule, edition, store


async def _enqueue(container, edition, event="edition_available"):
    async with container.session_factory() as session:
        await queue_edition_notifications(session, edition, container.clock.now(), event)
        await session.commit()


async def _rows(container):
    async with container.session_factory() as session:
        return list(await session.scalars(select(SubscriptionDeliveryRow)))


@pytest.mark.parametrize(
    "policy,event,expected",
    [
        (EditionEmailPolicy.NONE, "edition_available", 0),
        (EditionEmailPolicy.NONE, "material_change", 0),
        (EditionEmailPolicy.MATERIAL, "edition_available", 0),
        (EditionEmailPolicy.MATERIAL, "material_change", 1),
        (EditionEmailPolicy.EVERY, "edition_available", 1),
        (EditionEmailPolicy.EVERY, "material_change", 0),
    ],
)
async def test_policy_and_duplicate_enqueue_are_transactional(
    container, user, policy, event, expected
):
    _, edition, store = await setup_delivery(container, user, policy)
    await _enqueue(container, edition, event)
    await _enqueue(container, edition, event)
    sender = Sender()
    dispatcher = NotificationDispatcher(store, sender, container.clock)
    assert await dispatcher.tick() == expected
    assert await dispatcher.tick() == 0
    assert len(sender.messages) == expected
    assert len(await _rows(container)) == expected
    if expected:
        # Retrying publication after a recorded send neither conflicts nor resends.
        await _enqueue(container, edition, event)
        assert await dispatcher.tick() == 0
        message = sender.messages[0]
        assert "Daily research" not in message.body
        assert str(edition.id) in message.body
        assert "http://app.test/subscriptions" in message.body
        assert "evidence" not in message.body


@pytest.mark.parametrize(
    "revocation", ["account_optout", "subscription_optout", "deactivate", "remove"]
)
async def test_pending_send_rechecks_current_access_and_preferences(container, user, revocation):
    schedule, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition)
    claim = await store.claim(container.clock.now())
    assert claim is not None
    async with container.session_factory() as session:
        preferences = SqlNotificationPreferences(session)
        if revocation == "account_optout":
            await preferences.save_email(user.id, EmailPreferences())
        elif revocation == "subscription_optout":
            await preferences.save_subscription(
                user.id, schedule.id, SubscriptionEmailPreferences()
            )
        elif revocation == "deactivate":
            repos = container.repositories(session)
            fresh = await repos.users.lock_by_id(user.id)
            fresh.is_active = False
            await repos.users.save(fresh)
        else:
            row = await session.get(ScheduleRow, schedule.id)
            row.archived_at = container.clock.now()
        await session.commit()
    assert await store.prepare(claim, container.clock.now()) is None
    assert (await _rows(container))[0].state == "cancelled"


async def test_disabled_failed_uncertain_and_recorded_success(
    container: Container, user: User, clock: FakeClock
):
    _, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition)
    sender = Sender(available=False)
    dispatcher = NotificationDispatcher(store, sender, clock)
    await dispatcher.tick()
    assert not sender.messages
    row = (await _rows(container))[0]
    assert (row.state, row.attempts, row.safe_reason) == ("unavailable", 0, "email_not_configured")
    sender.available, sender.outcome = True, DeliveryOutcome.RETRYABLE
    clock.advance(timedelta(minutes=15))
    await dispatcher.tick()
    assert (await _rows(container))[0].state == "pending"
    clock.advance(timedelta(minutes=5))
    sender.outcome = DeliveryOutcome.UNCERTAIN
    await dispatcher.tick()
    assert (await _rows(container))[0].state == "uncertain"
    clock.advance(timedelta(days=1))
    assert await dispatcher.tick() == 0
    assert len(sender.messages) == 2


async def test_crash_after_claim_is_uncertain_not_retried(container, user, clock):
    _, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition)
    claim = await store.claim(clock.now())
    assert claim is not None
    assert await store.claim(clock.now()) is None
    clock.advance(timedelta(minutes=3))
    await store.recover_uncertain(clock.now())
    assert await store.claim(clock.now()) is None
    await store.finish(claim, DeliveryOutcome.RETRYABLE, clock.now())
    assert (await _rows(container))[0].state == "uncertain"


async def test_attention_transition_without_report_and_optout(container, user):
    _, edition, _store = await setup_delivery(container, user, EditionEmailPolicy.NONE)
    async with container.session_factory() as session:
        repository = SqlSubscriptionEditionRepository(session)
        advanced = replace(edition, workflow=EditionWorkflow.BLOCKED, revision=2)
        assert await repository.advance(advanced, expected_revision=1) is not None
        await session.commit()
    rows = await _rows(container)
    assert len(rows) == 1 and rows[0].event_kind == "attention"
    await _enqueue(container, edition, "attention")
    assert len(await _rows(container)) == 1


async def test_failed_attempts_stop_at_three_and_optin_names(container, user, clock):
    _, edition, store = await setup_delivery(container, user)
    async with container.session_factory() as session:
        await SqlNotificationPreferences(session).save_email(user.id, EmailPreferences(True, True))
        await session.commit()
    await _enqueue(container, edition)
    sender = Sender(DeliveryOutcome.RETRYABLE)
    dispatcher = NotificationDispatcher(store, sender, clock)
    for _ in range(4):
        await dispatcher.tick()
        clock.advance(timedelta(hours=1))
    assert len(sender.messages) == 3
    assert "Daily research" in sender.messages[0].body
    assert (await _rows(container))[0].state == "failed"


async def test_rolled_back_transition_does_not_publish_attention_intent(container, user):
    _, edition, _store = await setup_delivery(container, user)
    async with container.session_factory() as session:
        repository = SqlSubscriptionEditionRepository(session)
        advanced = replace(edition, workflow=EditionWorkflow.BLOCKED, revision=2)
        assert await repository.advance(advanced, expected_revision=1) is not None
        await session.rollback()
    assert await _rows(container) == []
    async with container.session_factory() as session:
        stored = await SqlSubscriptionEditionRepository(session).get(edition.id)
        assert stored is not None and stored.workflow is EditionWorkflow.PENDING

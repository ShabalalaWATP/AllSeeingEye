"""Opt-out then opt-in cannot resurrect an old intent, even before a worker observes it."""

import pytest

from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.application.account.notification_dispatch import NotificationDispatcher
from ase.domain.notification_delivery import (
    EditionEmailPolicy,
    EmailPreferences,
    SubscriptionEmailPreferences,
)
from test_notification_delivery import Sender, _enqueue, _rows, setup_delivery


@pytest.mark.parametrize("kind", ["account", "subscription", "attention"])
@pytest.mark.parametrize("claimed", [False, True])
async def test_optout_is_permanent_for_existing_intents(container, user, kind, claimed):
    schedule, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition, "attention" if kind == "attention" else "edition_available")
    claim = await store.claim(container.clock.now()) if claimed else None
    async with container.session_factory() as session:
        preferences = SqlNotificationPreferences(session)
        if kind == "account":
            await preferences.save_email(user.id, EmailPreferences(False))
            await preferences.save_email(user.id, EmailPreferences(True))
        else:
            await preferences.save_subscription(
                user.id, schedule.id, SubscriptionEmailPreferences()
            )
            await preferences.save_subscription(
                user.id, schedule.id, SubscriptionEmailPreferences(EditionEmailPolicy.EVERY, True)
            )
        await session.commit()
    if claim is not None:
        assert await store.prepare(claim, container.clock.now()) is None
    sender = Sender()
    await NotificationDispatcher(store, sender, container.clock).tick()
    assert not sender.messages
    assert (await _rows(container))[0].state == ("uncertain" if claimed else "cancelled")

"""One account opt-out permanently fences all three kinds of queued email."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from alert_routing_helpers import delivery_store, fire, outbox, rule, save_route
from ase.adapters.persistence.notification_digest_models import DigestPreferenceRow
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.container.notifications import digest_preferences, digest_worker
from ase.domain.notification_delivery import EmailPreferences
from ase.domain.notification_digest import DigestPreferences
from test_notification_delivery import _enqueue, _rows, setup_delivery
from test_notification_digest import _rows as digest_rows


@pytest.mark.parametrize("claimed", [False, True])
async def test_master_optout_fences_edition_digest_and_rule_email(client, container, user, claimed):
    headers, rule_id = await rule(client, user)
    _, edition, edition_store = await setup_delivery(container, user)
    await _enqueue(container, edition, "edition_available")
    async with container.session_factory() as session:
        await digest_preferences(container, session).save(user, DigestPreferences(True))
    await save_route(client, headers, rule_id)
    await fire(container, rule_id)
    container.clock.advance(timedelta(days=1))
    digest = digest_worker(container)
    assert await digest._store.enqueue_due(container.clock.now()) == 1
    rule_store = delivery_store(container)
    if claimed:
        for store in (edition_store, digest._dispatcher._store, rule_store):
            assert await store.claim(container.clock.now()) is not None

    async with container.session_factory() as session:
        preferences = SqlNotificationPreferences(session)
        await preferences.save_email(user.id, EmailPreferences(False))
        await preferences.save_email(user.id, EmailPreferences(True))
        await session.commit()

    expected = "uncertain" if claimed else "cancelled"
    assert [row.state for row in await _rows(container)] == [expected]
    assert [row.state for row in await digest_rows(container)] == [expected]
    assert [row.state for row in await outbox(container)] == [expected]
    for store in (edition_store, digest._dispatcher._store, rule_store):
        assert await store.claim(container.clock.now()) is None
    async with container.session_factory() as session:
        assert (
            await session.scalar(
                select(DigestPreferenceRow.enabled).where(DigestPreferenceRow.user_id == user.id)
            )
            is False
        )

"""Local-day windows, scope and post-claim opt-out guard daily digest delivery."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from ase.adapters.persistence.notification_digest_models import (
    DigestDeliveryRow,
    DigestPreferenceRow,
)
from ase.adapters.persistence.notification_digest_schedule import SqlDigestScheduler
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.container.notifications import digest_preferences, digest_worker
from ase.domain.notification_delivery import EmailPreferences
from ase.domain.notification_digest import DigestPreferences, latest_digest_slot, next_digest_at
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_notification_delivery import Sender, setup_delivery
from test_private_feed import _alert


async def _enable(container, user):
    await setup_delivery(container, user)
    async with container.session_factory() as session:
        await digest_preferences(container, session).save(user, DigestPreferences(True))


async def _rows(container):
    async with container.session_factory() as session:
        return list(await session.scalars(select(DigestDeliveryRow)))


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-03-28T02:00:00+00:00", "2026-03-29T01:00:00+00:00"),
        ("2026-10-24T02:00:00+00:00", "2026-10-25T00:00:00+00:00"),
    ],
)
def test_dst_uses_gap_first_valid_and_first_fold(instant, expected):
    preferences = DigestPreferences(True, "Europe/London", 1)
    slot = next_digest_at(datetime.fromisoformat(instant), preferences)
    assert slot == datetime.fromisoformat(expected)
    assert latest_digest_slot(slot, preferences).utc == slot
    # A fold's second occurrence is not another delivery day.
    assert next_digest_at(slot, preferences).date() == (slot + timedelta(days=1)).date()


async def test_saved_window_survives_repeat_scheduler_and_empty_period(container, user):
    await _enable(container, user)
    start = container.clock.now()
    container.clock.advance(timedelta(days=1))
    scheduler = SqlDigestScheduler(container.session_factory, container.access_policy)
    assert await scheduler.enqueue_due(container.clock.now()) == 1
    assert await scheduler.enqueue_due(container.clock.now()) == 0
    row = (await _rows(container))[0]
    assert row.window_start == start and row.window_end <= container.clock.now()
    worker = digest_worker(container)
    sender = Sender()
    worker._dispatcher._sender = sender
    assert await worker._dispatcher.tick() == 1
    assert not sender.messages
    assert (await _rows(container))[0].state == "empty"
    # Outage creates one current intent covering all missed time, not daily bursts.
    container.clock.advance(timedelta(days=5))
    assert await scheduler.enqueue_due(container.clock.now()) == 1
    rows = await _rows(container)
    assert len(rows) == 2
    assert rows[1].window_start == row.window_end


async def test_digest_full_counts_and_no_private_prose(container, user):
    await _enable(container, user)
    for _ in range(61):
        await _alert(container, user)
    container.clock.advance(timedelta(days=1))
    worker = digest_worker(container)
    await worker._store.enqueue_due(container.clock.now())
    sender = Sender()
    worker._dispatcher._sender = sender
    await worker._dispatcher.tick()
    assert len(sender.messages) == 1
    assert "Alerts: 61" in sender.messages[0].body
    assert "Private alert" not in sender.messages[0].body
    assert "SECRET" not in sender.messages[0].body
    assert await worker._dispatcher.tick() == 0


async def test_master_optout_after_claim_cancels_and_requires_new_optin(container, user):
    await _enable(container, user)
    await _alert(container, user)
    container.clock.advance(timedelta(days=1))
    worker = digest_worker(container)
    await worker._store.enqueue_due(container.clock.now())
    claim = await worker._dispatcher._store.claim(container.clock.now())
    async with container.session_factory() as session:
        await SqlNotificationPreferences(session).save_email(user.id, EmailPreferences())
        await session.commit()
    assert claim is not None
    assert await worker._dispatcher._store.prepare(claim, container.clock.now()) is None
    assert (await _rows(container))[0].safe_reason == "opted_out"
    async with container.session_factory() as session:
        row = await session.get(DigestPreferenceRow, user.id)
        assert row is not None and not row.enabled


async def test_api_off_by_default_requires_confirmed_email_and_valid_zone(client, container, user):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    path = "/api/me/notifications/digest"
    assert (await client.get(path, headers=headers)).json() == {
        "enabled": False,
        "timezone": "UTC",
        "hour": 8,
    }
    assert (await client.put(path, headers=headers, json={"enabled": True})).status_code == 422
    assert (
        await client.put(path, headers=headers, json={"timezone": "Invalid/Zone"})
    ).status_code == 422
    assert (await client.put(path, headers=headers, json={"hour": 24})).status_code == 422

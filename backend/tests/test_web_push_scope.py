"""Late alert commits, current team scope and device removal preserve push privacy."""

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete, select, update

from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_notification_scope import _team
from test_private_feed import _alert
from test_web_push import (
    PATH,
    Sender,
    configured,  # noqa: F401
    register,
    worker,
)

pytestmark = pytest.mark.usefixtures("configured")


async def test_later_commit_with_same_time_smaller_uuid_is_not_skipped(client, container, user):
    await register(client, container)
    now = container.clock.now()
    await _alert(container, user)
    larger, smaller = UUID(int=100), UUID(int=10)
    async with container.session_factory() as session:
        await session.execute(update(AlertRow).values(id=larger))
        await session.commit()
    sender = Sender()
    runner, _store = worker(container, sender)
    assert await runner.tick() == 1
    await _alert(container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(AlertRow).where(AlertRow.id != larger).values(id=smaller, fired_at=now)
        )
        await session.commit()
    container.clock.advance(timedelta(seconds=31))
    assert await runner.tick() == 1
    assert {message.alert_id for message in sender.messages} == {larger, smaller}
    container.clock.advance(timedelta(seconds=31))
    assert await runner.tick() == 0


async def test_revoked_membership_after_claim_cancels_alert_push(client, container, user):
    await register(client, container)
    team = await _team(container, user)
    await _alert(container, user)
    async with container.session_factory() as session:
        await session.execute(update(AlertRow).values(team_id=team))
        await session.commit()
    _runner, store = worker(container, Sender())
    await store.enqueue(container.clock.now())
    claim = await store.claim(container.clock.now())
    assert claim is not None
    async with container.session_factory() as session:
        await session.execute(delete(TeamMembershipRow).where(TeamMembershipRow.team_id == team))
        await session.commit()
    assert not await store.authorise(claim, container.clock.now())
    async with container.session_factory() as session:
        row = await session.get(PushDeliveryRow, claim.id)
        assert row.state == "cancelled"


async def test_device_deletion_is_scoped_and_permanent(client, container, user, admin):
    _claims, device = await register(client, container)
    administrator = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    path = f"{PATH}/{device['id']}"
    assert (await client.delete(path, headers=bearer(administrator))).status_code == 204
    async with container.session_factory() as session:
        assert await session.get(PushDeviceRow, UUID(device["id"])) is not None
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.delete(path, headers=bearer(token))).status_code == 204
    async with container.session_factory() as session:
        assert not list(await session.scalars(select(PushDeviceRow)))


async def test_interrupted_claim_becomes_uncertain_and_never_replays(client, container, user):
    await register(client, container)
    await _alert(container, user)
    sender = Sender()
    runner, store = worker(container, sender)
    await store.enqueue(container.clock.now())
    claim = await store.claim(container.clock.now())
    assert claim is not None
    container.clock.advance(timedelta(minutes=2))
    assert await runner.tick() == 0
    assert not await store.authorise(claim, container.clock.now())
    assert not sender.messages
    async with container.session_factory() as session:
        row = await session.get(PushDeliveryRow, claim.id)
        assert row.state == "uncertain"

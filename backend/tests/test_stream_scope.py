"""Private alert filtering and live membership invalidation on open streams."""

import asyncio
from dataclasses import replace
from uuid import uuid4

from httpx import AsyncClient

from ase.api.routers import stream as stream_router
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from ase.domain.warning import Alert
from helpers import USER_PASSWORD, login_token
from team_helpers import CONTEXT, team_service


async def test_stream_filters_personal_and_team_alerts_and_refreshes_membership(
    client: AsyncClient, container: Container, admin: User, user: User, monkeypatch
) -> None:
    monkeypatch.setattr(stream_router, "PING_SECONDS", 0.01)
    async with team_service(container) as service:
        team = await service.create(admin, "Private desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    token = await login_token(client, user.email, USER_PASSWORD)
    response = await stream_router.stream(user, container.issuer.verify(token), container)
    iterator = response.body_iterator
    alert = Alert(uuid4(), uuid4(), container.clock.now(), "Private", "", 1, 1, (), ())
    try:
        assert (await anext(iterator))["event"] == "hello"
        for private in (
            replace(alert, created_by=admin.id),
            replace(alert, created_by=admin.id, team_id=uuid4()),
            alert,  # Legacy orphan has no established owner.
        ):
            await container.bus.publish(BusMessage("alert", {"alert": private}))
        await container.bus.publish(BusMessage("event.expire", {"ids": []}))
        async with asyncio.timeout(2):
            assert (await anext(iterator))["event"] == "event.expire"
        shared = replace(alert, created_by=admin.id, team_id=team.id)
        await container.bus.publish(BusMessage("alert", {"alert": shared}))
        assert (await anext(iterator))["event"] == "alert"
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)
        # No data is needed: the idle heartbeat tells clients to clear scoped state.
        async with asyncio.timeout(2):
            assert (await anext(iterator))["event"] == "access.changed"
        await container.bus.publish(BusMessage("alert", {"alert": shared}))
        await container.bus.publish(BusMessage("event.expire", {"ids": []}))
        async with asyncio.timeout(2):
            assert (await anext(iterator))["event"] == "event.expire"
    finally:
        await iterator.aclose()
    assert container.streams.held(user.id) == 0


async def test_queued_alert_rechecks_membership_after_access_frame_yields(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Queued desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    token = await login_token(client, user.email, USER_PASSWORD)
    response = await stream_router.stream(user, container.issuer.verify(token), container)
    iterator = response.body_iterator
    alert = Alert(
        uuid4(),
        uuid4(),
        container.clock.now(),
        "Private",
        "",
        1,
        1,
        (),
        (),
        created_by=admin.id,
        team_id=team.id,
    )
    try:
        assert (await anext(iterator))["event"] == "hello"
        async with team_service(container) as service:
            await service.update(
                admin, team.id, name="Archived desk", is_active=False, context=CONTEXT
            )
        await container.bus.publish(BusMessage("alert", {"alert": alert}))
        assert (await anext(iterator))["event"] == "access.changed"
        # Simulate backpressure: authority is revoked while the generator is suspended.
        async with team_service(container) as service:
            await service.update(
                admin, team.id, name="Queued desk", is_active=True, context=CONTEXT
            )
            await service.remove_member(admin, team.id, user.id, CONTEXT)
        await container.bus.publish(BusMessage("event.expire", {"ids": []}))
        async with asyncio.timeout(2):
            assert (await anext(iterator))["event"] == "access.changed"
            assert (await anext(iterator))["event"] == "event.expire"
    finally:
        await iterator.aclose()

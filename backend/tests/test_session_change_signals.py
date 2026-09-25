"""Committed session and access changes are signalled; rollbacks and cosmetic edits are not."""

import asyncio
from dataclasses import replace
from datetime import timedelta

from httpx import AsyncClient

from ase.api.routers import stream as stream_router
from ase.application.ports.feeds import BusMessage
from ase.application.ports.session import SESSION_CHANGED
from ase.container import Container
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from helpers import USER_PASSWORD, login_token
from team_helpers import CONTEXT, team_service


def changed(container: Container, user: User, since) -> bool:
    return container.session_signals.changed_since(user.id, since)


async def test_a_committed_revocation_signals_and_wakes_streams(
    container: Container, user: User
) -> None:
    subscription = container.bus.subscribe()
    before = container.clock.now()
    try:
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.refresh_tokens.revoke_all_for_user(user.id, container.clock.now())
            assert not changed(container, user, before)  # Nothing before commit.
            await repos.uow.commit()
        assert changed(container, user, before)
        async with asyncio.timeout(1):
            message = await anext(aiter(subscription))
        assert message.kind == SESSION_CHANGED and message.payload == {"user_id": user.id}
    finally:
        subscription.close()


async def test_a_rolled_back_revocation_signals_nothing(container: Container, user: User) -> None:
    before = container.clock.now()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.refresh_tokens.revoke_all_for_user(user.id, container.clock.now())
        await session.rollback()
        await repos.uow.commit()
    assert not changed(container, user, before)


async def test_family_revocation_names_its_owner(
    client: AsyncClient, container: Container, user: User
) -> None:
    claims = container.issuer.verify(await login_token(client, user.email, USER_PASSWORD))
    before = container.clock.now()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.refresh_tokens.revoke_family(claims.family_id, container.clock.now())
        await repos.uow.commit()
    assert changed(container, user, before)


async def test_only_security_relevant_user_edits_signal(container: Container, user: User) -> None:
    before = container.clock.now()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.users.save(replace(user, display_name="Renamed"))
        await repos.uow.commit()
    assert not changed(container, user, before)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.users.save(replace(user, role=Role.MANAGER))
        await repos.uow.commit()
    assert changed(container, user, before)


async def test_membership_and_team_state_changes_signal_members(
    container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Signal desk", CONTEXT)
    before = container.clock.now()
    async with team_service(container) as service:
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    assert changed(container, user, before)
    container.clock.advance(timedelta(seconds=1))
    archived = container.clock.now()
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
    assert changed(container, user, archived)
    container.clock.advance(timedelta(seconds=1))
    removed = container.clock.now()
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=True, context=CONTEXT)
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    assert changed(container, user, removed)


async def test_streams_reuse_a_recent_check_for_public_deliveries(
    client: AsyncClient, container: Container, user: User, monkeypatch
) -> None:
    reads = 0
    original = stream_router._stream_access

    async def counted(*args):
        nonlocal reads
        reads += 1
        return await original(*args)

    monkeypatch.setattr(stream_router, "_stream_access", counted)
    token = await login_token(client, user.email, USER_PASSWORD)
    response = await stream_router.stream(user, container.issuer.verify(token), container)
    iterator = response.body_iterator
    try:
        assert (await anext(iterator))["event"] == "hello"
        for _ in range(5):
            await container.bus.publish(BusMessage("event.expire", {"ids": []}))
            async with asyncio.timeout(2):
                assert (await anext(iterator))["event"] == "event.expire"
        assert reads == 1  # Only the opening check; no per-message database reads.
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.refresh_tokens.revoke_all_for_user(user.id, container.clock.now())
            await repos.uow.commit()
        async with asyncio.timeout(2):
            frame = await anext(iterator)
        assert frame["event"] == "bye" and "session_revoked" in frame["data"]
        assert reads == 2
    finally:
        await iterator.aclose()

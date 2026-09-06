"""Actual transactions prevent manager mutations using authority revoked while waiting."""

import asyncio

import pytest

from ase.adapters.persistence.users import SqlUserRepository
from ase.container import Container
from ase.domain.errors import InvalidRequest, NotFound, Unauthenticated
from ase.domain.teams import MembershipRole
from ase.domain.users import Role
from helpers import create_user
from team_helpers import CONTEXT, team_service
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("revocation", ["membership", "account_role", "archive"])
async def test_waiting_manager_revalidates_authority(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
    revocation: str,
) -> None:
    container = race_container
    admin = await create_user(container, email="admin@example.com", password=None, role=Role.ADMIN)
    manager = await create_user(
        container, email="manager@example.com", password=None, role=Role.MANAGER
    )
    target = await create_user(container, email="target@example.com", password=None)
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MANAGER, context=CONTEXT
        )

    reached, release = asyncio.Event(), asyncio.Event()
    original = SqlUserRepository.lock_administration

    async def pause(self: SqlUserRepository) -> None:
        task = asyncio.current_task()
        if task is not None and task.get_name() == "waiting-manager":
            reached.set()
            await asyncio.wait_for(release.wait(), 10)
        await original(self)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", pause)

    async def add() -> None:
        async with team_service(container) as service:
            await service.set_member(
                manager, team.id, email=target.email, role=MembershipRole.MEMBER, context=CONTEXT
            )

    pending = asyncio.create_task(add(), name="waiting-manager")
    try:
        await asyncio.wait_for(reached.wait(), 10)
        if revocation == "account_role":
            async with container.session_factory() as session:
                await container.update_user(session).execute(
                    admin, manager.id, Role.USER, None, CONTEXT
                )
        else:
            async with team_service(container) as service:
                if revocation == "membership":
                    await service.remove_member(admin, team.id, manager.id, CONTEXT)
                else:
                    await service.update(
                        admin, team.id, name=None, is_active=False, context=CONTEXT
                    )
        release.set()
        with pytest.raises((NotFound, Unauthenticated, InvalidRequest)):
            await pending
    finally:
        release.set()
        await asyncio.gather(pending, return_exceptions=True)
    async with team_service(container) as service:
        assert target.id not in {
            member.user_id for member in (await service.roster(admin, team.id))[1]
        }


async def test_concurrent_duplicate_member_requests_keep_single_membership(
    race_container: Container,
) -> None:
    container = race_container
    admin = await create_user(container, email="admin@example.com", password=None, role=Role.ADMIN)
    target = await create_user(container, email="target@example.com", password=None)
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)

    async def add() -> None:
        async with team_service(container) as service:
            await service.set_member(
                admin, team.id, email=target.email, role=MembershipRole.MEMBER, context=CONTEXT
            )

    await asyncio.gather(add(), add())
    async with team_service(container) as service:
        assert [member.user_id for member in (await service.roster(admin, team.id))[1]] == [
            target.id
        ]

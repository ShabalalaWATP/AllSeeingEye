"""Actual transactions prevent manager mutations using authority revoked while waiting."""

import asyncio
import contextlib
from uuid import UUID

import pytest

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.container import Container
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from helpers import create_user
from team_helpers import CONTEXT, team_service
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("revocation", ["membership", "archive"])
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
        await service.set_member(
            admin, team.id, email=target.email, role=MembershipRole.MEMBER, context=CONTEXT
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

    async def promote() -> None:
        async with team_service(container) as service:
            await service.change_role(manager, team.id, target.id, MembershipRole.MANAGER, CONTEXT)

    pending = asyncio.create_task(promote(), name="waiting-manager")
    try:
        await asyncio.wait_for(reached.wait(), 10)
        async with team_service(container) as service:
            if revocation == "membership":
                await service.remove_member(admin, team.id, manager.id, CONTEXT)
            else:
                await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
        release.set()
        with pytest.raises((NotFound, Unauthenticated, InvalidRequest)):
            await pending
    finally:
        release.set()
        await asyncio.gather(pending, return_exceptions=True)
    async with team_service(container) as service:
        roster = {
            member.user_id: member.role for member in (await service.roster(admin, team.id))[1]
        }
        assert roster[target.id] is MembershipRole.MEMBER


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
        roster = await service.roster(admin, team.id)
        assert [member.user_id for member in roster[1]].count(target.id) == 1


@pytest.mark.parametrize("operation", ["demote", "leave", "remove"])
async def test_concurrent_changes_cannot_remove_the_last_active_manager(
    race_container: Container, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Two Managers act on each other (or leave) at once; exactly one may succeed."""
    container = race_container
    arrivals: list[int] = []
    both_counted = asyncio.Event()
    original = SqlTeamRepository.count_active_managers

    async def widen_window(self: SqlTeamRepository, team_id: UUID) -> int:
        # Without serialisation both requests would reach the count before either
        # writes. Wait briefly for that interleaving; the guard should prevent it.
        arrivals.append(1)
        if len(arrivals) >= 2:
            both_counted.set()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(both_counted.wait(), 0.5)
        return await original(self, team_id)

    monkeypatch.setattr(SqlTeamRepository, "count_active_managers", widen_window)
    admin = await create_user(container, email="admin@example.com", password=None, role=Role.ADMIN)
    first = await create_user(container, email="first@example.com", password=None)
    second = await create_user(container, email="second@example.com", password=None)
    async with team_service(container) as service:
        team = await service.create(first, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=second.email, role=MembershipRole.MANAGER, context=CONTEXT
        )

    async def act(actor: User, other: User) -> None:
        async with team_service(container) as service:
            if operation == "demote":
                await service.change_role(actor, team.id, other.id, MembershipRole.MEMBER, CONTEXT)
            elif operation == "remove":
                await service.remove_member(actor, team.id, other.id, CONTEXT)
            else:
                await service.leave(actor, team.id, CONTEXT)

    results = await asyncio.gather(act(first, second), act(second, first), return_exceptions=True)
    failures = [result for result in results if isinstance(result, BaseException)]
    assert len(failures) == 1, results
    # The loser either sees the invariant or, after removal, lost its authority.
    assert isinstance(failures[0], (InvalidRequest, NotFound, Forbidden))
    async with team_service(container) as service:
        members = (await service.roster(admin, team.id))[1]
        assert [member.role for member in members].count(MembershipRole.MANAGER) == 1

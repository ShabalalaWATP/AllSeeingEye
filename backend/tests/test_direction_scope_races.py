"""A direction mutation waiting for authority cannot use a revoked team membership."""

import asyncio

import pytest

from ase.adapters.persistence.users import SqlUserRepository
from ase.application.direction.plans import PirInput, PlanInput
from ase.container import Container
from ase.domain.errors import Forbidden, NotFound
from ase.domain.teams import MembershipRole
from ase.domain.users import Role
from helpers import create_user
from team_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("change", ["revoke", "archive"])
async def test_waiting_plan_create_rechecks_team_authority(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    container = race_container
    admin = await create_user(container, email="admin@example.com", password=None, role=Role.ADMIN)
    owner = await create_user(container, email="owner@example.com", password=None)
    async with container.session_factory() as session:
        team = await container.teams(session).create(admin, "Team", CONTEXT)
        await container.teams(session).set_member(
            admin, team.id, email=owner.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    reached, release = asyncio.Event(), asyncio.Event()
    original = SqlUserRepository.lock_administration

    async def pause(repository: SqlUserRepository) -> None:
        task = asyncio.current_task()
        if task is not None and task.get_name() == "waiting-plan":
            reached.set()
            await asyncio.wait_for(release.wait(), 10)
        await original(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", pause)

    async def create() -> None:
        async with container.session_factory() as session:
            await container.create_plan(session).execute(
                owner, PlanInput("Plan", pirs=(PirInput("Question"),), team_id=team.id), CONTEXT
            )

    pending = asyncio.create_task(create(), name="waiting-plan")
    try:
        await asyncio.wait_for(reached.wait(), 10)
        async with container.session_factory() as session:
            if change == "revoke":
                await container.teams(session).remove_member(admin, team.id, owner.id, CONTEXT)
            else:
                await container.teams(session).update(
                    admin, team.id, name=None, is_active=False, context=CONTEXT
                )
        release.set()
        with pytest.raises((Forbidden, NotFound)):
            await pending
    finally:
        release.set()
        await asyncio.gather(pending, return_exceptions=True)
    async with container.session_factory() as session:
        assert await container.repositories(session).plans.list_all() == []

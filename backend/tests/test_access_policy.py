"""The shared access policy distinguishes ownership, membership and management capability."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.access import AccessContext
from ase.application.direction.areas import AoiInput
from ase.application.direction.plans import PirInput, PlanInput
from ase.container import Container
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.teams import MembershipRole, Team
from ase.domain.users import Role, User
from team_helpers import CONTEXT


def team_context(
    user: User,
    container: Container,
    *,
    active: bool = True,
    membership: MembershipRole = MembershipRole.MEMBER,
) -> tuple[AccessContext, Team]:
    team = Team(uuid4(), "Team", active, user.id, container.clock.now(), container.clock.now())
    return AccessContext(user, {team.id: team}, {team.id: membership}), team


async def test_orphan_legacy_scope_is_admin_only(
    container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        policy = container.access_policy(session)
        ordinary = await policy.context(user)
        for operation in (ordinary.require_read, ordinary.require_write):
            with pytest.raises(NotFound):
                operation(None, None)
        administrator = await policy.context(admin)
        administrator.require_read(None, None)
        administrator.require_write(None, None)
        assert administrator.visibility.administrator
        assert ordinary.visibility.user_id == user.id


def test_manager_requires_team_designation_only(container: Container, user: User) -> None:
    unrelated_owner = uuid4()
    for role, membership in (
        (Role.USER, MembershipRole.MEMBER),
        (Role.MANAGER, MembershipRole.MEMBER),
    ):
        decision, team = team_context(replace(user, role=role), container, membership=membership)
        decision.require_read(unrelated_owner, team.id)
        with pytest.raises(Forbidden):
            decision.require_write(unrelated_owner, team.id)
    decision, team = team_context(
        replace(user, role=Role.USER), container, membership=MembershipRole.MANAGER
    )
    decision.require_write(unrelated_owner, team.id)
    with pytest.raises(NotFound):
        decision.require_write(unrelated_owner, None)
    with pytest.raises(NotFound):
        decision.require_create(uuid4())


def test_same_scope_never_allows_cross_owner_personal_link(
    container: Container, admin: User, user: User
) -> None:
    decision, team = team_context(admin, container)
    decision.require_same_scope(user.id, team.id, uuid4(), team.id)
    for left_owner, left_team, right_owner, right_team in (
        (user.id, None, admin.id, None),
        (None, None, None, None),
        (user.id, None, user.id, team.id),
        (user.id, team.id, user.id, uuid4()),
    ):
        with pytest.raises(InvalidRequest):
            decision.require_same_scope(left_owner, left_team, right_owner, right_team)


async def test_background_requires_active_owner_and_active_current_membership(
    container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        team = await container.teams(session).create(user, "Team", CONTEXT)
        policy = container.access_policy(session)
        await policy.background(user.id, None)
        with pytest.raises(Forbidden):
            await policy.background(admin.id, team.id)
        decision = await policy.background(user.id, team.id, for_update=True)
        assert decision.visibility.team_ids == (team.id,)
        await session.rollback()
        await container.teams(session).update(
            admin, team.id, name=None, is_active=False, context=CONTEXT
        )
        with pytest.raises(Forbidden):
            await policy.background(user.id, team.id)
        with pytest.raises(Unauthenticated):
            await policy.background(uuid4(), None)
        with pytest.raises(Unauthenticated):
            await policy.context(replace(user, security_version=-1))
        with pytest.raises(Unauthenticated):
            await policy.context(replace(user, id=uuid4()), for_update=True)


async def test_legacy_cross_owner_plan_aoi_is_retained_but_not_used(
    container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        aoi = await container.create_aoi(session).execute(
            admin, AoiInput("Private", "countries", countries=("UA",)), CONTEXT
        )
        plan = await container.create_plan(session).execute(
            user, PlanInput("Legacy", pirs=(PirInput("Question"),)), CONTEXT
        )
        repository = container.repositories(session).plans
        await repository.save(replace(plan, aoi_id=aoi.id))
        await session.commit()
        with pytest.raises(NotFound):
            await container.plan_evidence(session).execute(user, plan.id)
        with pytest.raises(InvalidRequest):
            await container.plan_evidence(session).execute(admin, plan.id)
        assert (await repository.get(plan.id)).aoi_id == aoi.id

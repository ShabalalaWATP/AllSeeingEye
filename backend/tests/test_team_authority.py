"""Team authority: roster privacy, direct add, inactive Managers and deactivation."""

from dataclasses import replace

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.directory_profile import DirectoryProfile
from ase.domain.errors import Conflict, Forbidden, InvalidRequest
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from helpers import create_user
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import WarningActors, create_schedule
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414

ADMIN_CONTEXT = RequestContext(ip="127.0.0.1", user_agent=None)


async def _deactivate(container: Container, admin: User, target: User) -> User:
    async with container.session_factory() as session:
        return await container.update_user(session).execute(
            admin, target.id, None, False, ADMIN_CONTEXT
        )


async def test_roster_shows_directory_handle_and_never_login_email(
    container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        await container.repositories(session).directory_profiles.save(
            DirectoryProfile(user.id, username="field_analyst")
        )
        await session.commit()
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        _, roster = await service.roster(user, team.id)
    by_id = {member.user_id: member for member in roster}
    assert by_id[user.id].username == "field_analyst"
    assert by_id[admin.id].username is None
    assert not any(hasattr(member, "email") for member in roster)


async def test_manager_direct_add_is_refused_without_revealing_the_target(
    container: Container, admin: User, user: User
) -> None:
    inactive = await create_user(
        container, email="inactive@example.com", password=None, is_active=False
    )
    async with team_service(container) as service:
        team = await service.create(user, "Self-service", CONTEXT)
        messages = set()
        for email in (admin.email, inactive.email, "missing@example.com", "not-an-email"):
            with pytest.raises(Forbidden) as caught:
                await service.set_member(
                    user, team.id, email=email, role=MembershipRole.MEMBER, context=CONTEXT
                )
            messages.add(str(caught.value))
        assert len(messages) == 1


async def test_administrator_direct_add_is_audited(
    container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    async with container.session_factory() as session:
        rows = list(
            await session.scalars(
                select(AuditLogRow).where(AuditLogRow.action == "team_member_set")
            )
        )
    assert rows[-1].details == {"user_id": str(user.id), "role": "member", "direct_add": True}


async def test_sole_active_manager_can_demote_and_remove_inactive_managers(
    container: Container, admin: User, user: User
) -> None:
    dormant = await create_user(container, email="dormant@example.com", password=None)
    departed = await create_user(container, email="departed@example.com", password=None)
    async with team_service(container) as service:
        team = await service.create(user, "Desk", CONTEXT)
        for target in (dormant, departed):
            await service.set_member(
                admin, team.id, email=target.email, role=MembershipRole.MANAGER, context=CONTEXT
            )
    async with container.session_factory() as session:
        repos = container.repositories(session)
        for target in (dormant, departed):
            await repos.users.save(replace(target, is_active=False))
        await repos.uow.commit()
    async with team_service(container) as service:
        await service.change_role(user, team.id, dormant.id, MembershipRole.MEMBER, CONTEXT)
        await service.remove_member(user, team.id, departed.id, CONTEXT)
        with pytest.raises(InvalidRequest, match="active account"):
            await service.change_role(user, team.id, dormant.id, MembershipRole.MANAGER, CONTEXT)
        with pytest.raises(InvalidRequest, match="retain at least one"):
            await service.leave(user, team.id, CONTEXT)
        roles = {member.user_id: member.role for member in (await service.roster(user, team.id))[1]}
    assert roles == {user.id: MembershipRole.MANAGER, dormant.id: MembershipRole.MEMBER}


async def test_deactivating_the_last_active_manager_requires_a_replacement_or_archive(
    container: Container, admin: User, user: User
) -> None:
    deputy = await create_user(container, email="deputy@example.com", password=None)
    async with team_service(container) as service:
        first = await service.create(user, "First", CONTEXT)
        second = await service.create(user, "Second", CONTEXT)
    with pytest.raises(Conflict, match="only active Manager of 2 active team"):
        await _deactivate(container, admin, user)
    async with team_service(container) as service:
        await service.update(user, first.id, name=None, is_active=False, context=CONTEXT)
        await service.set_member(
            admin, second.id, email=deputy.email, role=MembershipRole.MANAGER, context=CONTEXT
        )
    # The archived team and the team with a deputy no longer block deactivation.
    assert not (await _deactivate(container, admin, user)).is_active
    # The deputy is now the only active Manager of the remaining active team.
    with pytest.raises(Conflict, match="1 active team"):
        await _deactivate(container, admin, deputy)


async def test_global_manager_role_cannot_be_assigned(
    container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="retired"):
            await container.update_user(session).execute(
                admin, user.id, Role.MANAGER, None, ADMIN_CONTEXT
            )


@pytest.mark.parametrize("departure", ["removal", "leave"])
async def test_departed_member_scheduled_team_dispatch_stops(
    container: Container, admin: User, warning_actors: WarningActors, departure: str
) -> None:
    """Subscription admission and the schedule store both use the background recheck."""
    actors = warning_actors
    schedule = await create_schedule(container, actors.owner, actors.team.id)
    store = SqlScheduleStore(container.session_factory, container.access_policy)
    assert await store.can_run(schedule)
    async with team_service(container) as service:
        if departure == "removal":
            await service.remove_member(actors.manager, actors.team.id, actors.owner.id, CONTEXT)
        else:
            await service.leave(actors.owner, actors.team.id, CONTEXT)
    assert not await store.can_run(schedule)
    async with container.session_factory() as session:
        with pytest.raises(Forbidden, match="current membership"):
            await container.access_policy(session).background(
                actors.owner.id, actors.team.id, for_update=True
            )

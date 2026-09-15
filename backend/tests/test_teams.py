"""Team membership is an explicit authority boundary, independent of account capability."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.teams import TeamMembershipRow
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from helpers import FakeClock, create_user
from team_helpers import CONTEXT, team_service


@pytest.fixture
async def manager(container: Container) -> User:
    return await create_user(
        container, email="manager@example.com", password=None, role=Role.MANAGER
    )


async def test_admin_creates_renames_archives_and_audits(container: Container, admin: User) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "  West desk  ", CONTEXT)
        assert team.name == "West desk"
        assert (await service.list_teams(admin))[0].id == team.id
        team = await service.update(
            admin, team.id, name="East desk", is_active=False, context=CONTEXT
        )
        assert team.name == "East desk" and not team.is_active
        assert (await service.get(admin, team.id)).id == team.id
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 20)
        assert {entry.action for entry in entries} >= {
            AuditAction.TEAM_CREATED,
            AuditAction.TEAM_UPDATED,
        }


async def test_any_active_user_can_create_and_manage_their_own_team(
    container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Private", CONTEXT)
        assert await service.list_teams(user) == []
        with pytest.raises(NotFound):
            await service.roster(user, team.id)
        own = await service.create(user, "Escalation", CONTEXT)
        assert [item.id for item in await service.list_teams(user)] == [own.id]
        assert (await service.roster(user, own.id))[1][0].role is MembershipRole.MANAGER
        # A team Manager cannot alter a site Administrator's membership.
        with pytest.raises(Forbidden):
            await service.set_member(
                user, own.id, email=admin.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
        with pytest.raises(NotFound):
            await service.update(user, team.id, name="Taken", is_active=None, context=CONTEXT)


async def test_team_manager_membership_grants_management_without_global_role(
    container: Container, admin: User, manager: User, user: User
) -> None:
    async with team_service(container) as service:
        led = await service.create(admin, "Led", CONTEXT)
        other = await service.create(admin, "Other", CONTEXT)
        for team, role in ((led, MembershipRole.MANAGER), (other, MembershipRole.MEMBER)):
            await service.set_member(
                admin, team.id, email=manager.email, role=role, context=CONTEXT
            )
            await service.set_member(
                admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
        await service.change_role(manager, led.id, user.id, MembershipRole.MANAGER, CONTEXT)
        await service.change_role(manager, led.id, user.id, MembershipRole.MEMBER, CONTEXT)
        with pytest.raises(Forbidden):
            await service.change_role(manager, other.id, user.id, MembershipRole.MANAGER, CONTEXT)
        outsider_team = await service.create(admin, "Outsider", CONTEXT)
        with pytest.raises(NotFound):
            await service.change_role(
                manager, outsider_team.id, admin.id, MembershipRole.MEMBER, CONTEXT
            )
        # Team leadership is a membership capability, independent of the
        # legacy global Manager role.
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.users.save(replace(manager, role=Role.USER))
        await repos.uow.commit()
    async with team_service(container) as service:
        await service.remove_member(manager, led.id, user.id, CONTEXT)


async def test_team_manager_can_manage_non_admin_accounts_but_not_admins(
    container: Container, admin: User, manager: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MANAGER, context=CONTEXT
        )
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        await service.change_role(manager, team.id, user.id, MembershipRole.MANAGER, CONTEXT)
        await service.change_role(manager, team.id, user.id, MembershipRole.MEMBER, CONTEXT)
        with pytest.raises(Forbidden):
            await service.change_role(manager, team.id, admin.id, MembershipRole.MEMBER, CONTEXT)
        with pytest.raises(Forbidden):
            await service.remove_member(manager, team.id, admin.id, CONTEXT)


async def test_members_read_roster_and_revocation_removes_access(
    container: Container, admin: User, user: User, manager: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MANAGER, context=CONTEXT
        )
        await service.set_member(
            admin, team.id, email=user.email.upper(), role=MembershipRole.MEMBER, context=CONTEXT
        )
        assert [item.id for item in await service.list_teams(user)] == [team.id]
        _, roster = await service.roster(user, team.id)
        assert {item.user_id for item in roster} == {admin.id, manager.id, user.id}
        with pytest.raises(Forbidden):
            await service.remove_member(user, team.id, user.id, CONTEXT)
        await service.remove_member(manager, team.id, user.id, CONTEXT)
        assert await service.list_teams(user) == []
        with pytest.raises(NotFound):
            await service.roster(user, team.id)
        with pytest.raises(NotFound):
            await service.remove_member(admin, team.id, user.id, CONTEXT)


async def test_archive_retains_reads_but_blocks_membership_mutations(
    container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
        assert not (await service.get(user, team.id)).is_active
        assert len((await service.roster(user, team.id))[1]) == 2
        with pytest.raises(InvalidRequest):
            await service.set_member(
                admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
        with pytest.raises(InvalidRequest):
            await service.remove_member(admin, team.id, user.id, CONTEXT)
        await service.update(admin, team.id, name=None, is_active=True, context=CONTEXT)
        await service.remove_member(admin, team.id, user.id, CONTEXT)


async def test_duplicate_add_is_idempotent_preserving_joined_at(
    container: Container, admin: User, manager: User, clock: FakeClock
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        first = await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        clock.advance(timedelta(days=1))
        second = await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MANAGER, context=CONTEXT
        )
        assert second.joined_at == first.joined_at
        assert len((await service.roster(admin, team.id))[1]) == 2
    async with container.session_factory() as session:
        session.add(
            TeamMembershipRow(
                team_id=team.id, user_id=manager.id, role="member", joined_at=clock.now()
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()


async def test_unknown_inactive_invalid_targets_and_stale_actor(
    container: Container, admin: User, user: User
) -> None:
    inactive = await create_user(
        container, email="inactive@example.com", password=None, is_active=False
    )
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
        for email in ("missing@example.com", inactive.email, "bad", "a @example.com", "x" * 321):
            with pytest.raises(InvalidRequest):
                await service.set_member(
                    admin, team.id, email=email, role=MembershipRole.MEMBER, context=CONTEXT
                )
        with pytest.raises(Unauthenticated):
            await service.create(replace(admin, security_version=-1), "Stale", CONTEXT)
        with pytest.raises(Unauthenticated):
            await service.list_teams(inactive)
        with pytest.raises(Unauthenticated):
            await service.list_teams(replace(user, id=uuid4()))


@pytest.mark.parametrize("name", ["", " ", "x" * 121, "Hidden\nname"])
async def test_invalid_names_rejected(container: Container, admin: User, name: str) -> None:
    async with team_service(container) as service:
        with pytest.raises(InvalidRequest):
            await service.create(admin, name, CONTEXT)
        team = await service.create(admin, "Valid", CONTEXT)
        with pytest.raises(InvalidRequest):
            await service.update(admin, team.id, name=name, is_active=None, context=CONTEXT)
        with pytest.raises(InvalidRequest):
            await service.update(admin, team.id, name=None, is_active=None, context=CONTEXT)
        with pytest.raises(NotFound):
            await service.update(admin, uuid4(), name="Missing", is_active=None, context=CONTEXT)


async def test_membership_role_constraint(container: Container, admin: User, user: User) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Desk", CONTEXT)
    async with container.session_factory() as session:
        session.add(
            TeamMembershipRow(
                team_id=team.id, user_id=user.id, role="admin", joined_at=container.clock.now()
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
    async with container.session_factory() as session:
        rows = list(await session.scalars(select(TeamMembershipRow)))
        assert len(rows) == 1
        assert rows[0].team_id == team.id and rows[0].user_id == admin.id
        assert rows[0].role == "manager"


async def test_last_manager_cannot_be_demoted_removed_or_leave(
    container: Container, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(user, "Protected", CONTEXT)
        with pytest.raises(InvalidRequest, match="retain at least one"):
            await service.change_role(user, team.id, user.id, MembershipRole.MEMBER, CONTEXT)
        with pytest.raises(InvalidRequest, match="retain at least one"):
            await service.remove_member(user, team.id, user.id, CONTEXT)

    with pytest.raises(InvalidRequest, match="retain at least one"):
        async with team_service(container) as service:
            await service.leave(user, team.id, CONTEXT)


async def test_manager_can_rename_and_archive_but_cannot_restore(
    container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Editable", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MANAGER, context=CONTEXT
        )
        renamed = await service.update(
            user,
            team.id,
            name="Renamed",
            is_active=None,
            description="Shared OSINT desk",
            context=CONTEXT,
        )
        assert renamed.name == "Renamed" and renamed.description == "Shared OSINT desk"
        cleared = await service.update(
            user,
            team.id,
            name=None,
            is_active=None,
            description=None,
            context=CONTEXT,
        )
        assert cleared.description is None
        archived = await service.update(user, team.id, name=None, is_active=False, context=CONTEXT)
        assert not archived.is_active
        with pytest.raises(InvalidRequest):
            await service.update(user, team.id, name="Nope", is_active=None, context=CONTEXT)
        restored = await service.update(admin, team.id, name=None, is_active=True, context=CONTEXT)
        assert restored.is_active


async def test_member_can_leave_and_admin_self_leave_is_protected(
    container: Container, admin: User, user: User
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Leave", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        await service.leave(user, team.id, CONTEXT)
        with pytest.raises(NotFound):
            await service.roster(user, team.id)
        with pytest.raises(Forbidden, match="another Administrator"):
            await service.leave(admin, team.id, CONTEXT)


async def test_account_team_creation_cap_counts_only_active_owned_teams(
    container: Container, user: User
) -> None:
    async with team_service(container) as service:
        archived = await service.create(user, "Archived", CONTEXT)
        await service.update(user, archived.id, name=None, is_active=False, context=CONTEXT)
        for number in range(5):
            await service.create(user, f"Desk {number}", CONTEXT)
        with pytest.raises(InvalidRequest, match="at most 5 active teams"):
            await service.create(user, "Overflow", CONTEXT)

"""Reactivation cannot produce an active team without an active Manager."""

from uuid import uuid4

import pytest

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.domain.errors import Forbidden, InvalidRequest
from ase.domain.teams import MembershipRole
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service


async def test_reactivation_requires_an_active_manager(container, user, admin):
    async with team_service(container) as teams:
        team = await teams.create(user, "Owner team", CONTEXT)
    async with team_service(container) as teams:
        await teams.update(user, team.id, name=None, is_active=False, context=CONTEXT)
    async with container.session_factory() as session:
        await container.update_user(session).execute(admin, user.id, None, False, CONTEXT)
    async with team_service(container) as teams:
        with pytest.raises(InvalidRequest, match="active Manager"):
            await teams.update(admin, team.id, name=None, is_active=True, context=CONTEXT)
    async with container.session_factory() as session:
        stored = await SqlTeamRepository(session).get(team.id)
        assert stored is not None and not stored.is_active


@pytest.mark.parametrize("existing", [False, True])
async def test_administrator_can_appoint_manager_atomically_during_reactivation(
    client, container, user, admin, existing
):
    replacement = await create_user(container, email="replacement@example.com", password=None)
    async with team_service(container) as teams:
        team = await teams.create(user, "Owner team", CONTEXT)
        if existing:
            await teams.set_member(
                admin, team.id, email=replacement.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
        await teams.update(user, team.id, name=None, is_active=False, context=CONTEXT)
    async with container.session_factory() as session:
        await container.update_user(session).execute(admin, user.id, None, False, CONTEXT)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        f"/api/teams/{team.id}",
        headers=bearer(token),
        json={"is_active": True, "reactivation_manager_id": str(replacement.id)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is True
    async with container.session_factory() as session:
        teams = SqlTeamRepository(session)
        assert await teams.count_active_managers(team.id) == 1
        membership = await teams.get_membership(team.id, replacement.id)
        assert membership is not None and membership.role is MembershipRole.MANAGER


@pytest.mark.parametrize("target", ["inactive", "missing", "self"])
async def test_recovery_refuses_ineligible_manager_without_reactivating(
    container, user, admin, target
):
    async with team_service(container) as teams:
        team = await teams.create(user, "Owner team", CONTEXT)
        await teams.update(user, team.id, name=None, is_active=False, context=CONTEXT)
    async with container.session_factory() as session:
        await container.update_user(session).execute(admin, user.id, None, False, CONTEXT)
    selected = user.id if target == "inactive" else admin.id if target == "self" else uuid4()
    async with team_service(container) as teams:
        with pytest.raises((InvalidRequest, Forbidden)):
            await teams.update(
                admin,
                team.id,
                name=None,
                is_active=True,
                reactivation_manager_id=selected,
                context=CONTEXT,
            )
    async with container.session_factory() as session:
        team = await SqlTeamRepository(session).get(team.id)
        assert team is not None and not team.is_active


async def test_recovery_is_not_an_alternative_to_ordinary_roster_authority(container, user, admin):
    async with team_service(container) as teams:
        team = await teams.create(user, "Owner team", CONTEXT)
        for actor in (user, admin):
            with pytest.raises(InvalidRequest, match="administrator reactivation"):
                await teams.update(
                    actor,
                    team.id,
                    name=None,
                    is_active=True,
                    reactivation_manager_id=user.id,
                    context=CONTEXT,
                )


@pytest.mark.parametrize("existing", [False, True])
async def test_recovery_respects_roster_cap_but_can_promote_existing_member(
    container, user, admin, monkeypatch, existing
):
    replacement = await create_user(container, email="replacement@example.com", password=None)
    async with team_service(container) as teams:
        team = await teams.create(user, "Owner team", CONTEXT)
        if existing:
            await teams.set_member(
                admin, team.id, email=replacement.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
        await teams.update(user, team.id, name=None, is_active=False, context=CONTEXT)

    async def full_roster(self, team_id):
        return 100

    monkeypatch.setattr(SqlTeamRepository, "count_members", full_roster)
    async with team_service(container) as teams:
        if existing:
            saved = await teams.update(
                admin,
                team.id,
                name=None,
                is_active=True,
                reactivation_manager_id=replacement.id,
                context=CONTEXT,
            )
            assert saved.is_active
        else:
            with pytest.raises(InvalidRequest, match="100 members"):
                await teams.update(
                    admin,
                    team.id,
                    name=None,
                    is_active=True,
                    reactivation_manager_id=replacement.id,
                    context=CONTEXT,
                )

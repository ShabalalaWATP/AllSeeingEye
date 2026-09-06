"""Team report access, immutable scope and revocation during model work."""

import pytest
from httpx import AsyncClient

from ase.application.dto import RequestContext
from ase.application.reports.request import ReportRequest
from ase.container import Container
from ase.domain.errors import NotFound
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from helpers import USER_PASSWORD, bearer, create_user, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_documents_helpers import document_records
from report_helpers import PROFILE, ScriptedGateway
from team_helpers import CONTEXT, team_service


async def team_for(container: Container, admin: User, user: User):
    async with team_service(container) as service:
        team = await service.create(admin, "Analysis desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        return team


async def save_team_report(container: Container, user: User, team_id):
    record, version = document_records(user.id)
    record.team_id = team_id
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record


async def test_member_reads_team_report_but_removed_creator_loses_access(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    team = await team_for(container, admin, user)
    # Admin-authored team work is shared with current members.
    record = await save_team_report(container, admin, team.id)
    own = await save_team_report(container, user, team.id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (await client.get(f"/api/reports/{record.id}", headers=headers)).status_code == 200
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    for item in (record, own):
        response = await client.get(f"/api/reports/{item.id}?version=1", headers=headers)
        assert response.status_code == 404
    assert (await client.get("/api/reports", headers=headers)).json()["items"] == []


async def test_manager_may_delete_team_contribution_only_when_assigned_to_lead(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    team = await team_for(container, admin, user)
    manager = await create_user(
        container, email="deskmanager@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    async with team_service(container) as service:
        await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    record = await save_team_report(container, user, team.id)
    headers = bearer(await login_token(client, manager.email, USER_PASSWORD))
    assert (await client.delete(f"/api/reports/{record.id}", headers=headers)).status_code == 403
    async with team_service(container) as service:
        await service.set_member(
            admin, team.id, email=manager.email, role=MembershipRole.MANAGER, context=CONTEXT
        )
    assert (await client.delete(f"/api/reports/{record.id}", headers=headers)).status_code == 204


@pytest.mark.parametrize("regenerate", [False, True])
async def test_membership_revoked_during_model_call_cannot_persist_report(
    client: AsyncClient, container: Container, admin: User, user: User, regenerate: bool
) -> None:
    team = await team_for(container, admin, user)
    record = await save_team_report(container, user, team.id)
    await seed_legacy_profile(container, PROFILE)

    class RevokingGateway(ScriptedGateway):
        async def complete(self, base_url, api_key, model, request):
            async with team_service(container) as service:
                await service.remove_member(admin, team.id, user.id, CONTEXT)
            return await super().complete(base_url, api_key, model, request)

    container.llm = RevokingGateway("{}", "{}")
    async with container.session_factory() as session:
        generation = container.generate_report(session)
        with pytest.raises(NotFound):
            if regenerate:
                await generation.regenerate(user, record.id, RequestContext())
            else:
                await generation.execute(
                    user, ReportRequest("intsum", team_id=team.id), RequestContext()
                )
    async with container.session_factory() as session:
        records = await container.repositories(session).reports.list_recent(20)
        assert [(item.id, item.latest_version) for item in records] == [(record.id, 1)]


async def test_archived_team_can_be_read_but_not_regenerated(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    team = await team_for(container, admin, user)
    record = await save_team_report(container, user, team.id)
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (await client.get(f"/api/reports/{record.id}", headers=headers)).status_code == 200
    assert (
        await client.post(f"/api/reports/{record.id}/versions", headers=headers)
    ).status_code == 403

"""Disposable rehearsal of supported personal report export/removal and deactivation."""

from httpx import AsyncClient
from sqlalchemy import func, select

from ase.adapters.persistence.operational_models import ReportRow, ReportVersionRow
from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records
from test_report_team_scope import save_team_report, team_for


async def test_record_level_removal_preserves_shared_work(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    team = await team_for(container, admin, user)
    shared = await save_team_report(container, user, team.id)
    own, own_version = document_records(user.id)
    own.title = "Personal export rehearsal"
    other, other_version = document_records(admin.id)
    other.title = "Other account private report"
    async with container.session_factory() as session:
        reports = container.repositories(session).reports
        await reports.add(own, own_version)
        await reports.add(other, other_version)
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(ReportRow)) == 3
        assert await session.scalar(select(func.count()).select_from(ReportVersionRow)) == 3

    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    export = await client.get(f"/api/reports/{own.id}/markdown?version=1", headers=headers)
    assert export.status_code == 200
    assert own.title in export.text
    assert other.title not in export.text
    assert (
        await client.get(f"/api/reports/{other.id}/markdown", headers=headers)
    ).status_code == 404
    assert (await client.delete(f"/api/reports/{other.id}", headers=headers)).status_code == 404
    assert (await client.delete(f"/api/reports/{own.id}", headers=headers)).status_code == 204
    assert (await client.get(f"/api/reports/{own.id}", headers=headers)).status_code == 404

    admin_headers = bearer(await login_token(client, admin.email, ADMIN_PASSWORD))
    response = await client.patch(
        f"/api/admin/users/{user.id}", json={"is_active": False}, headers=admin_headers
    )
    assert response.status_code == 200
    assert (await client.get("/api/me", headers=headers)).status_code == 401
    assert (await client.get(f"/api/reports/{shared.id}", headers=admin_headers)).status_code == 200
    assert (await client.get(f"/api/reports/{other.id}", headers=admin_headers)).status_code == 200
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportRow)) == 2
        assert await session.scalar(select(func.count()).select_from(ReportVersionRow)) == 2
        assert await container.repositories(session).users.get_by_id(user.id) is not None

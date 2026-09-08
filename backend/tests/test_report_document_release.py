"""Rendered document bytes require a live request session at release."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from ase.application.reports.exports import ExportReportUseCase
from ase.container import Container
from ase.domain.report_documents import ExportFormat, ReportFile
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, csrf_headers, login_token
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for


@pytest.mark.parametrize("format", [ExportFormat.PDF, ExportFormat.DOCX])
@pytest.mark.parametrize("change", ["expiry", "logout"])
async def test_document_release_refuses_session_changed_after_render(
    client: AsyncClient,
    container: Container,
    user: User,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
    format: ExportFormat,
    change: str,
) -> None:
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    execute = ExportReportUseCase.execute
    rendered: list[bytes] = []

    async def finish_then_change_session(
        self: ExportReportUseCase,
        actor: User,
        report_id: UUID,
        format: ExportFormat,
        number: int | None = None,
    ) -> ReportFile:
        result = await execute(self, actor, report_id, format, number)
        rendered.append(result.content)
        if change == "expiry":
            clock.advance(timedelta(minutes=16))
        else:
            response = await client.post("/api/auth/logout", headers=csrf_headers(client))
            assert response.status_code == 204
        return result

    monkeypatch.setattr(ExportReportUseCase, "execute", finish_then_change_session)
    response = await client.get(
        f"/api/reports/{record.id}/export/{format.value}", headers=bearer(token)
    )
    assert len(rendered) == 1 and rendered[0]
    assert response.status_code == 401
    assert response.content != rendered[0]
    assert "content-disposition" not in response.headers


@pytest.mark.parametrize("change", ["delete_report", "remove_membership"])
async def test_document_release_refuses_object_access_lost_after_render(
    client, container, user, admin, monkeypatch, change
):
    team = await team_for(container, admin, user) if change == "remove_membership" else None
    record, version = document_records(user.id)
    record.team_id = team.id if team else None
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    execute = ExportReportUseCase.execute
    rendered = []

    async def finish_then_change_access(self, actor, report_id, format, number=None):
        result = await execute(self, actor, report_id, format, number)
        rendered.append(result.content)
        if team:
            async with team_service(container) as service:
                await service.remove_member(admin, team.id, user.id, CONTEXT)
        else:
            response = await client.delete(f"/api/reports/{report_id}", headers=bearer(token))
            assert response.status_code == 204, response.text
        return result

    monkeypatch.setattr(ExportReportUseCase, "execute", finish_then_change_access)
    response = await client.get(f"/api/reports/{record.id}/export/docx", headers=bearer(token))
    assert rendered and response.content != rendered[0]
    assert response.status_code == 404, response.text
    assert "content-disposition" not in response.headers


@pytest.mark.parametrize("missing", [True, False])
async def test_document_release_requires_exact_rendered_version_metadata(
    client, container, user, monkeypatch, missing
):
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    execute = ExportReportUseCase.execute

    async def changed_metadata(self, actor, report_id, format, number=None):
        rendered = await execute(self, actor, report_id, format, number)
        return replace(rendered, report_version_id=None if missing else uuid4())

    monkeypatch.setattr(ExportReportUseCase, "execute", changed_metadata)
    response = await client.get(f"/api/reports/{record.id}/export/docx", headers=bearer(token))
    assert response.status_code == 409
    assert "content-disposition" not in response.headers

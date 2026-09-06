"""Real evidence-package HTTP routes preserve report scope and recheck before byte release."""

import asyncio
import io
import json
import zipfile
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.container import Container
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service
from test_report_team_scope import save_team_report, team_for


async def save_versions(container: Container, owner: User) -> tuple[ReportRecord, ReportVersion]:
    record, first = document_records(owner.id)
    record.latest_version = 2
    latest = replace(first, id=uuid4(), number=2, markdown="# Second frozen version\n")
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.reports.add(record, first)
        await repos.reports.add_version(record, latest)
        await session.commit()
    return record, first


async def test_personal_package_authentication_owner_isolation_and_historical_bytes(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    record, first = await save_versions(container, user)
    path = f"/api/reports/{record.id}/evidence-package"
    assert (await client.get(path)).status_code == 401
    other = await create_user(container, email="other-package@example.com", password=USER_PASSWORD)
    other_headers = bearer(await login_token(client, other.email, USER_PASSWORD))
    denied = await client.get(path, headers=other_headers)
    assert denied.status_code == 404
    assert "content-disposition" not in denied.headers
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get(path, params={"version": 1}, headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="evidence-{record.id}-v1.zip"'
    )
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.read("report.md").decode() == first.markdown
        assert json.loads(archive.read("manifest.json"))["version_id"] == str(first.id)
    latest = await client.get(path, headers=headers)
    with zipfile.ZipFile(io.BytesIO(latest.content)) as archive:
        assert archive.read("report.md").decode() == "# Second frozen version\n"
    assert (await client.get(path, params={"version": 9}, headers=headers)).status_code == 404
    assert (await client.get(path, params={"version": 0}, headers=headers)).status_code == 422


async def test_team_package_requires_current_membership_including_for_its_creator(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    team = await team_for(container, admin, user)
    record = await save_team_report(container, user, team.id)
    path = f"/api/reports/{record.id}/evidence-package?version=1"
    stranger = await create_user(
        container, email="nonmember-package@example.com", password=USER_PASSWORD
    )
    stranger_headers = bearer(await login_token(client, stranger.email, USER_PASSWORD))
    assert (await client.get(path, headers=stranger_headers)).status_code == 404
    member_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    allowed = await client.get(path, headers=member_headers)
    assert allowed.status_code == 200 and allowed.content.startswith(b"PK")
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    denied = await client.get(path, headers=member_headers)
    assert denied.status_code == 404
    assert not denied.content.startswith(b"PK")


@pytest.mark.parametrize("revoke_membership", [False, True])
async def test_package_does_not_release_bytes_after_access_changes_during_render(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    revoke_membership: bool,
) -> None:
    team = await team_for(container, admin, user)
    record = await save_team_report(container, user, team.id)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    started, release = Event(), Event()
    original = FrozenEvidencePackageRenderer.render

    def blocked(self, report, version):
        started.set()
        if not release.wait(5):
            raise TimeoutError("Synthetic renderer barrier was not released")
        return original(self, report, version)

    monkeypatch.setattr(FrozenEvidencePackageRenderer, "render", blocked)
    request = asyncio.create_task(
        client.get(
            f"/api/reports/{record.id}/evidence-package?version=1",
            headers=bearer(token),
        )
    )
    try:
        assert await asyncio.to_thread(started.wait, 3)
        if revoke_membership:
            async with team_service(container) as service:
                await service.remove_member(admin, team.id, user.id, CONTEXT)
        else:
            # Revoke only the original family: the account and membership stay valid,
            # so the route's explicit original-session release check is exercised.
            claims = container.issuer.verify(token)
            async with container.session_factory() as session:
                repos = container.repositories(session)
                await repos.refresh_tokens.revoke_family(claims.family_id, container.clock.now())
                await repos.uow.commit()
    finally:
        release.set()
    response = await asyncio.wait_for(request, 5)
    assert response.status_code == (404 if revoke_membership else 401)
    assert not response.content.startswith(b"PK")
    assert "content-disposition" not in response.headers
    assert response.headers["content-type"].startswith("application/json")

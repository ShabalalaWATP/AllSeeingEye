"""A team copy exports its own identity and cannot outlive membership authority."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.reports.stix import ExportStix
from ase.domain.teams import MembershipRole
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service
from test_stix_export import cyber_records

READER_EMAIL = "stix-reader@example.com"
READER_PASSWORD = "Fixture-Stix-Reader-904"  # gitleaks:allow


@pytest.mark.parametrize("revoke_during_render", [False, True])
async def test_team_copy_stix_provenance_and_release(
    client, container, user, admin, monkeypatch, revoke_during_render
):
    reader = await create_user(container, email=READER_EMAIL, password=READER_PASSWORD)
    async with team_service(container) as service:
        team = await service.create(admin, "Cyber analysis desk", CONTEXT)
    for member in (user, reader):
        async with team_service(container) as service:
            await service.set_member(
                admin, team.id, email=member.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
    record, version = cyber_records(user.id)
    private_parent = uuid4()
    record = replace(record, scope={"parent_report_id": str(private_parent)})
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    owner_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    copied = await client.post(
        f"/api/reports/{record.id}/versions/1/team-copies",
        json={"team_id": str(team.id)},
        headers=owner_headers,
    )
    assert copied.status_code == 201, copied.text
    copy_id = copied.json()["report_id"]
    reader_headers = bearer(await login_token(client, READER_EMAIL, READER_PASSWORD))
    provenance = await client.get(
        f"/api/reports/{copy_id}/team-copy-provenance", headers=reader_headers
    )
    assert provenance.status_code == 200
    assert provenance.json()["source_report_id"] is None
    original = await client.get(
        f"/api/reports/{record.id}/stix?version=1&tlp=amber", headers=reader_headers
    )
    assert original.status_code == 404
    owner_export = await client.get(
        f"/api/reports/{record.id}/stix?version=1&tlp=amber", headers=owner_headers
    )
    assert owner_export.status_code == 200
    original_report = next(row for row in owner_export.json()["objects"] if row["type"] == "report")

    execute = ExportStix.execute
    rendered = []

    async def finish(self, *args):
        result = await execute(self, *args)
        rendered.append(result.content)
        if revoke_during_render:
            async with team_service(container) as service:
                await service.remove_member(admin, team.id, reader.id, CONTEXT)
        return result

    monkeypatch.setattr(ExportStix, "execute", finish)
    response = await client.get(
        f"/api/reports/{copy_id}/stix?version=1&tlp=amber", headers=reader_headers
    )
    assert len(rendered) == 1
    if revoke_during_render:
        assert response.status_code == 404
        assert response.content != rendered[0]
        assert "content-disposition" not in response.headers
        return
    assert response.status_code == 200, response.text
    report = next(row for row in response.json()["objects"] if row["type"] == "report")
    assert report["id"] != original_report["id"]
    assert "Frozen ASE report version 1" in report["description"]
    assert "TLP:AMBER" in report["description"]
    assert f"Report {copy_id} \\| version 1" in report["description"]
    assert str(record.id) not in response.text
    assert str(version.id) not in response.text
    assert str(private_parent) not in response.text
    assert json.loads(rendered[0]) == response.json()

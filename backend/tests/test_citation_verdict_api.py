"""Human citation verdicts: exact-version anchors, scope, IDOR, archive and audit rules."""

import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

import ase.application.reports.citation_verdicts as service
from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.teams import SqlTeamRepository, TeamMembershipRow
from ase.domain.users import Role
from citation_verdict_helpers import MEMBER, make_team, seed_verdict_report, verdict_payload
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token


async def _headers(client, account, password=USER_PASSWORD):
    return bearer(await login_token(client, account.email, password))


async def test_owner_records_lists_and_verdicts_never_change_the_frozen_version(
    container, client, user
):
    record, version, path = await seed_verdict_report(container, user.id)
    headers = await _headers(client, user)
    empty = await client.get(path, headers=headers)
    assert empty.status_code == 200, empty.text
    assert empty.json()["verdicts"] == [] and empty.json()["can_record"] is True
    assert empty.headers["cache-control"] == "private, no-store"
    created = await client.post(path, headers=headers, json=verdict_payload())
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["verdict"] == "supports" and body["reviewer_id"] == str(user.id)
    assert (body["judgement_id"], body["label"], body["relation"]) == ("KJ1", "E1", "supporting")
    assert body["version_number"] == 1 and body["report_version_id"] == str(version.id)
    container.clock.advance(timedelta(seconds=1))
    correction = await client.post(
        path, headers=headers, json=verdict_payload(verdict="partly_supports", note=None)
    )
    assert correction.status_code == 201
    listed = (await client.get(path, headers=headers)).json()
    assert [row["verdict"] for row in listed["verdicts"]] == ["supports", "partly_supports"]
    assert "human opinions" in listed["notice"]
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 1)
        assert saved.body == version.body and saved.citation_checks == version.citation_checks
        assert saved.assessment == version.assessment and saved.markdown == version.markdown
        audits = (
            await session.scalars(
                select(AuditLogRow).where(AuditLogRow.action == "citation_verdict_recorded")
            )
        ).all()
    assert len(audits) == 2
    assert audits[0].details == {"report_id": str(record.id), "version": 1, "verdict": "supports"}
    assert "excerpt states" not in json.dumps([row.details for row in audits])


async def test_verdict_is_tied_to_its_exact_version_and_survives_regeneration(
    container, client, user
):
    record, version, path = await seed_verdict_report(container, user.id)
    headers = await _headers(client, user)
    assert (await client.post(path, headers=headers, json=verdict_payload())).status_code == 201
    second = replace(version, id=uuid4(), number=2)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add_version(
            replace(record, latest_version=2), second
        )
        await session.commit()
    later = await client.get(path.replace("/versions/1/", "/versions/2/"), headers=headers)
    assert later.status_code == 200 and later.json()["verdicts"] == []
    kept = (await client.get(path, headers=headers)).json()["verdicts"]
    assert len(kept) == 1 and kept[0]["report_version_id"] == str(version.id)


async def test_boundary_validation_rejects_uncited_anchors_and_injected_fields(
    container, client, user
):
    _, _, path = await seed_verdict_report(container, user.id)
    headers = await _headers(client, user)
    for change in (
        {"note": "x" * 301},
        {"verdict": "true"},
        {"relation": "neutral"},
        {"reviewer_id": str(uuid4())},
        {"recorded_at": "2020-01-01T00:00:00Z"},
        {"label": ""},
    ):
        response = await client.post(path, headers=headers, json=verdict_payload(**change))
        assert response.status_code == 422, change
    for change in (
        {"label": "E3"},
        {"judgement_id": "KJ9"},
        {"relation": "contradicting"},
    ):
        response = await client.post(path, headers=headers, json=verdict_payload(**change))
        assert response.status_code == 422, change
        assert "citation recorded on this saved judgement" in response.json()["error"]["message"]
    missing = path.replace("/versions/1/", "/versions/7/")
    assert (await client.get(missing, headers=headers)).status_code == 404


async def test_other_accounts_cannot_read_record_or_export_personal_verdicts(
    container, client, user
):
    _, _, path = await seed_verdict_report(container, user.id)
    headers = await _headers(client, user)
    assert (await client.post(path, headers=headers, json=verdict_payload())).status_code == 201
    other = await create_user(container, email="verdict-other@example.com", password=USER_PASSWORD)
    foreign = await _headers(client, other)
    assert (await client.get(path, headers=foreign)).status_code == 404
    assert (await client.get(path + "/export", headers=foreign)).status_code == 404
    assert (await client.post(path, headers=foreign, json=verdict_payload())).status_code == 404
    unknown = path.replace(path.split("/")[3], str(uuid4()))
    assert (await client.get(unknown, headers=headers)).status_code == 404
    assert (await client.get(path)).status_code == 401


async def test_team_verdicts_follow_current_membership_and_archive_is_read_only(
    container, client, user, admin
):
    reviewer = await create_user(
        container, email="verdict-member@example.com", password=USER_PASSWORD
    )
    team_id = await make_team(container, ((user, MEMBER), (reviewer, MEMBER)))
    _, _, path = await seed_verdict_report(container, user.id, team_id=team_id)
    member = await _headers(client, reviewer)
    created = await client.post(path, headers=member, json=verdict_payload(verdict="cannot_tell"))
    assert created.status_code == 201, created.text
    assert created.json()["team_id"] == str(team_id)
    async with container.session_factory() as session:
        team = await SqlTeamRepository(session).get(team_id)
        team.is_active = False
        await SqlTeamRepository(session).save(team)
        await session.commit()
    archived = await client.get(path, headers=member)
    assert archived.status_code == 200 and archived.json()["can_record"] is False
    assert (await client.post(path, headers=member, json=verdict_payload())).status_code == 403
    administrator = await _headers(client, admin, ADMIN_PASSWORD)
    override = await client.post(path, headers=administrator, json=verdict_payload())
    assert override.status_code == 201, override.text
    async with container.session_factory() as session:
        await session.delete(await session.get(TeamMembershipRow, (team_id, reviewer.id)))
        await session.commit()
    assert (await client.get(path, headers=member)).status_code == 404
    assert (await client.get(path + "/export", headers=member)).status_code == 404


async def test_manager_role_is_not_needed_but_non_members_are_refused(container, client, user):
    manager = await create_user(
        container, email="verdict-manager@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    team_id = await make_team(container, ((user, MEMBER),))
    _, _, path = await seed_verdict_report(container, user.id, team_id=team_id)
    outsider = await _headers(client, manager)
    assert (await client.post(path, headers=outsider, json=verdict_payload())).status_code == 404


async def test_export_is_a_bound_jsonl_labelled_set(container, client, user):
    record, version, path = await seed_verdict_report(container, user.id)
    headers = await _headers(client, user)
    for verdict in ("supports", "does_not_support"):
        await client.post(path, headers=headers, json=verdict_payload(verdict=verdict))
        container.clock.advance(timedelta(seconds=1))
    await client.post(path, headers=headers, json=verdict_payload(label="E2", verdict="supports"))
    exported = await client.get(path + "/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("application/x-ndjson")
    assert exported.headers["cache-control"] == "private, no-store"
    assert f"citation-verdicts-{record.id}-v1.jsonl" in exported.headers["content-disposition"]
    lines = [json.loads(line) for line in exported.text.splitlines()]
    header, rows = lines[0], lines[1:]
    assert header["record"] == "header" and header["verdicts"] == 3
    assert header["dataset"] == "ase-report-citation-verdicts-v1"
    assert "human opinions" in header["notice"]
    assert [row["current"] for row in rows] == [False, True, True]
    first = rows[0]
    statement = version.body.key_judgements[0].statement
    assert first["judgement_statement"] == statement
    assert first["excerpt"]["text"] == version.evidence[0].title[:12]
    assert first["source_id"] == version.evidence[0].source_id
    assert len(first["binding_sha256"]) == 64
    assert rows[2]["label"] == "E2" and rows[2]["binding_sha256"] != first["binding_sha256"]


async def test_capacity_limits_are_explicit(container, client, user, monkeypatch):
    monkeypatch.setattr(service, "MAX_CITATION_VERDICTS", 1)
    _, _, path = await seed_verdict_report(container, user.id)
    headers = await _headers(client, user)
    assert (await client.post(path, headers=headers, json=verdict_payload())).status_code == 201
    full = await client.post(path, headers=headers, json=verdict_payload())
    assert full.status_code == 422 and "verdict limit" in full.json()["error"]["message"]
    monkeypatch.setattr(service, "MAX_VERSION_VERDICTS", 1)
    full = await client.post(path, headers=headers, json=verdict_payload(label="E2"))
    assert full.status_code == 422 and "verdict limit" in full.json()["error"]["message"]

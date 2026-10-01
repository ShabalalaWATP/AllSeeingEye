"""Copying a finished personal version to a team: access, disclosure, provenance, retries."""

from sqlalchemy import func, select

from ase.adapters.persistence.models import AuditLogRow, LlmUsageRow, ReportRow
from ase.adapters.persistence.report_team_copy_models import ReportTeamCopyRow
from ase.domain.reports import ReportStatus
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)
from team_copy_helpers import PRIVATE_LABEL, count, seed_personal, team_with
from team_helpers import CONTEXT, team_service

COLLEAGUE_EMAIL = "colleague@example.com"
COLLEAGUE_PASSWORD = "Harbour-Lights-Glow-77"  # gitleaks:allow


def copy_url(report_id, number=1):
    return f"/api/reports/{report_id}/versions/{number}/team-copies"


async def test_owner_copies_a_version_that_team_members_read_and_export(
    client, container, user, admin
):
    colleague = await create_user(container, email=COLLEAGUE_EMAIL, password=COLLEAGUE_PASSWORD)
    team = await team_with(container, admin, user, colleague)
    record, version = await seed_personal(container, user.id)
    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    preview = await client.get(
        f"/api/reports/{record.id}/versions/1/team-copy-preview?team_id={team.id}", headers=owner
    )
    assert preview.status_code == 200
    shown = preview.json()
    assert [row["label"] for row in shown["private_inputs"]] == [PRIVATE_LABEL]
    assert set(shown["omissions"]) >= {"research_brief", "original_passages", "scope_references"}
    assert shown["existing_report_id"] is None and shown["team_name"] == "Analysis desk"
    body = {"team_id": str(team.id), "disclosed_evidence_labels": [PRIVATE_LABEL]}
    created = await client.post(copy_url(record.id), json=body, headers=owner)
    assert created.status_code == 201, created.text
    copy_id = created.json()["report_id"]
    assert created.json()["created"] is True and copy_id != str(record.id)

    reader = bearer(await login_token(client, COLLEAGUE_EMAIL, COLLEAGUE_PASSWORD))
    read = await client.get(f"/api/reports/{copy_id}", headers=reader)
    assert read.status_code == 200, read.text
    copied = read.json()
    assert copied["report"]["team_id"] == str(team.id)
    assert [item["content_hash"] for item in copied["version"]["evidence"]] == [
        item.content_hash for item in version.evidence
    ]
    exported = await client.get(f"/api/reports/{copy_id}/markdown", headers=reader)
    assert exported.status_code == 200
    # IDOR: the team-only reader still cannot reach the personal original or copy it.
    assert (await client.get(f"/api/reports/{record.id}", headers=reader)).status_code == 404
    assert (await client.post(copy_url(record.id), json=body, headers=reader)).status_code == 404
    provenance = (
        await client.get(f"/api/reports/{copy_id}/team-copy-provenance", headers=reader)
    ).json()
    assert provenance["source_report_id"] is None
    assert provenance["copied_by"] == str(user.id) and provenance["copied_by_name"] == "User"
    assert provenance["source_version_number"] == 1
    assert provenance["disclosed_private_inputs"] == 1
    own = (await client.get(f"/api/reports/{copy_id}/team-copy-provenance", headers=owner)).json()
    assert own["source_report_id"] == str(record.id)
    missing = await client.get(f"/api/reports/{record.id}/team-copy-provenance", headers=owner)
    assert missing.status_code == 404
    # The personal original is unchanged and no model was called.
    original = (await client.get(f"/api/reports/{record.id}", headers=owner)).json()
    assert original["report"]["team_id"] is None
    assert await count(container, select(func.count()).select_from(LlmUsageRow)) == 0
    audited = await count(
        container,
        select(func.count()).where(AuditLogRow.action == "report_copied_to_team"),
    )
    assert audited == 1


async def test_retry_returns_the_existing_copy_without_a_duplicate(client, container, user, admin):
    team = await team_with(container, admin, user)
    record, _ = await seed_personal(container, user.id, private_input=False)
    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = {"team_id": str(team.id)}
    first = await client.post(copy_url(record.id), json=body, headers=owner)
    again = await client.post(copy_url(record.id), json=body, headers=owner)
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["report_id"] == first.json()["report_id"]
    assert again.json()["created"] is False
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 1
    preview = await client.get(
        f"/api/reports/{record.id}/versions/1/team-copy-preview?team_id={team.id}", headers=owner
    )
    assert preview.json()["existing_report_id"] == first.json()["report_id"]


async def test_private_input_evidence_needs_the_exact_disclosure(client, container, user, admin):
    team = await team_with(container, admin, user)
    record, _ = await seed_personal(container, user.id)
    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    for labels in ([], ["E1"], [PRIVATE_LABEL, "E1"]):
        refused = await client.post(
            copy_url(record.id),
            json={"team_id": str(team.id), "disclosed_evidence_labels": labels},
            headers=owner,
        )
        assert refused.status_code == 422, labels
    invalid = await client.post(
        copy_url(record.id),
        json={"team_id": str(team.id), "disclosed_evidence_labels": ["<b>"]},
        headers=owner,
    )
    assert invalid.status_code == 422
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 0


async def test_only_the_owner_may_copy_and_only_to_an_active_membership(
    client, container, user, admin
):
    colleague = await create_user(container, email=COLLEAGUE_EMAIL, password=COLLEAGUE_PASSWORD)
    member_team = await team_with(container, admin, user, colleague, name="Member desk")
    other_team = await team_with(container, admin, name="Other desk")
    record, _ = await seed_personal(container, user.id, private_input=False)
    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    administrator = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    reader = bearer(await login_token(client, COLLEAGUE_EMAIL, COLLEAGUE_PASSWORD))
    member_body = {"team_id": str(member_team.id)}
    # Non-owner team member: the personal report is not even visible.
    assert (
        await client.post(copy_url(record.id), json=member_body, headers=reader)
    ).status_code == 404
    # Administrators have no override that widens someone else's personal work.
    refused = await client.post(copy_url(record.id), json=member_body, headers=administrator)
    assert refused.status_code == 403
    # Not a member of the target team.
    other = await client.post(
        copy_url(record.id), json={"team_id": str(other_team.id)}, headers=owner
    )
    assert other.status_code == 404
    # Archived target team.
    async with container.session_factory() as session:
        current_admin = await container.repositories(session).users.get_by_id(admin.id)
    async with team_service(container) as service:
        await service.update(
            current_admin, member_team.id, name=None, is_active=False, context=CONTEXT
        )
    archived = await client.post(copy_url(record.id), json=member_body, headers=owner)
    assert archived.status_code == 403
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 0


async def test_team_reports_failed_versions_and_unknown_versions_are_refused(
    client, container, user, admin
):
    team = await team_with(container, admin, user)
    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = {"team_id": str(team.id)}
    failed, _ = await seed_personal(
        container, user.id, private_input=False, status=ReportStatus.FAILED
    )
    assert (await client.post(copy_url(failed.id), json=body, headers=owner)).status_code == 422
    assert (await client.post(copy_url(failed.id, 2), json=body, headers=owner)).status_code == 404
    created = await client.post(
        copy_url((await seed_personal(container, user.id, private_input=False))[0].id),
        json=body,
        headers=owner,
    )
    copied = created.json()["report_id"]
    # A team report is not a personal source, even for its creator.
    assert (await client.post(copy_url(copied), json=body, headers=owner)).status_code == 422


async def test_removing_membership_removes_access_to_the_copy(client, container, user, admin):
    colleague = await create_user(container, email=COLLEAGUE_EMAIL, password=COLLEAGUE_PASSWORD)
    team = await team_with(container, admin, user, colleague)
    record, _ = await seed_personal(container, user.id, private_input=False)
    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    copied = (
        await client.post(copy_url(record.id), json={"team_id": str(team.id)}, headers=owner)
    ).json()["report_id"]
    reader = bearer(await login_token(client, COLLEAGUE_EMAIL, COLLEAGUE_PASSWORD))
    assert (await client.get(f"/api/reports/{copied}", headers=reader)).status_code == 200
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, colleague.id, CONTEXT)
    assert (await client.get(f"/api/reports/{copied}", headers=reader)).status_code == 404
    gone = await client.get(f"/api/reports/{copied}/team-copy-provenance", headers=reader)
    assert gone.status_code == 404
    # Deleting the team copy removes its provenance, so the version can be copied again.
    assert (await client.delete(f"/api/reports/{copied}", headers=owner)).status_code == 204
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 0
    assert await count(container, select(func.count()).select_from(ReportRow)) == 1

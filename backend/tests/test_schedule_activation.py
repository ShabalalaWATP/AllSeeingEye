"""Schedule controls preserve pinned definitions, due slots and retained work."""

from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.auditing import Auditor
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.teams import MembershipRole
from ase.domain.users import Role
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from report_job_api_helpers import prepared
from team_helpers import CONTEXT, team_service
from test_research_brief_api import _draft


async def test_pause_and_resume_keep_due_slot_and_are_idempotent(client, container, user) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    created = await client.post(
        "/api/schedules",
        json={"name": "Cadence", "template_id": "intsum", "country_iso": "UA"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    schedule = created.json()
    path = f"/api/schedules/{schedule['id']}"

    paused = await client.post(f"{path}/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    assert paused.json()["enabled"] is False
    assert paused.json()["next_run_at"] == schedule["next_run_at"]
    assert (await client.post(f"{path}/pause", headers=headers)).json() == paused.json()
    container.clock.advance(timedelta(days=2))
    assert await container.schedule_runner.run_once() == 0

    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    resumed = await client.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["enabled"] is True
    assert resumed.json()["next_run_at"] == schedule["next_run_at"]
    assert (await client.post(f"{path}/resume", headers=headers)).json() == resumed.json()
    assert await container.schedule_runner.run_once() == 1
    assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(UUID(schedule["id"]))
        audits = list(
            await session.scalars(select(AuditLogRow).where(AuditLogRow.subject == schedule["id"]))
        )
    assert len([edition for edition in editions if edition.job_id is not None]) == 1
    assert [
        row.details.get("action")
        for row in audits
        if row.details.get("action") in {"pause", "resume"}
    ] == ["pause", "resume"]


async def test_brief_linked_pause_resumes_active_job_without_changing_frozen_revision(
    client, container, user
) -> None:
    _, headers = await prepared(container, client)
    draft = _draft()
    saved = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert saved.status_code == 201, saved.text
    brief_id = saved.json()["brief"]["identity"]["id"]
    created = await client.post(
        "/api/schedules/from-brief",
        json={
            "brief_id": brief_id,
            "brief_revision": 1,
            "timezone": "Europe/London",
            "local_hour": 9,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    schedule = created.json()
    schedule_id = UUID(schedule["id"])
    due = schedule["next_run_at"]
    container.clock.advance(
        datetime.fromisoformat(due) - container.clock.now() + timedelta(minutes=1)
    )
    assert await container.schedule_runner.run_once() == 1
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        edition = await ledger.active(schedule_id)
        assert edition is not None and edition.job_id is not None
        frozen = await ledger.get_revision(schedule_id, edition.frozen_revision)
        assert frozen is not None
        jobs = SqlReportJobRepository(session)
        job = await jobs.get(edition.job_id)
        assert job is not None
        claimed = await jobs.claim(
            job.id,
            expected_revision=job.revision,
            lease_token=uuid4(),
            now=container.clock.now(),
            lease_until=container.clock.now() + timedelta(seconds=45),
        )
        assert claimed is not None and claimed.status == "running"
        running = await ledger.advance(
            replace(
                edition,
                workflow=EditionWorkflow.RUNNING,
                updated_at=container.clock.now(),
                revision=edition.revision + 1,
            ),
            expected_revision=edition.revision,
        )
        assert running is not None
        await session.commit()

    paused = await client.post(f"/api/schedules/{schedule_id}/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    assert (paused.json()["brief_id"], paused.json()["brief_revision"]) == (brief_id, 1)
    assert paused.json()["next_run_at"] != due  # The admitted due slot already advanced.
    next_due = paused.json()["next_run_at"]
    async with container.session_factory() as session:
        current = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(edition.job_id)
        current_frozen = await SqlSubscriptionEditionRepository(session).get_revision(
            schedule_id, edition.frozen_revision
        )
    assert current is not None and current.workflow is EditionWorkflow.PAUSED
    assert current.safe_reason == "schedule_paused"
    assert job is not None and job.status == "paused"
    assert current_frozen == frozen

    paused_again = await client.post(f"/api/schedules/{schedule_id}/pause", headers=headers)
    assert paused_again.status_code == 200 and paused_again.json() == paused.json()
    async with container.session_factory() as session:
        repeated = await SqlSubscriptionEditionRepository(session).get(edition.id)
    assert repeated is not None and repeated.revision == current.revision

    resumed = await client.post(f"/api/schedules/{schedule_id}/resume", headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["next_run_at"] == next_due
    assert (resumed.json()["brief_id"], resumed.json()["brief_revision"]) == (brief_id, 1)
    async with container.session_factory() as session:
        current = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(edition.job_id)
    assert current is not None and current.workflow is EditionWorkflow.QUEUED
    assert job is not None and job.status == "queued"
    assert (
        await client.post(f"/api/schedules/{schedule_id}/resume", headers=headers)
    ).status_code == 200

    manual = await client.post(
        f"/api/schedules/{schedule_id}/editions/{edition.id}/pause", headers=headers
    )
    assert manual.status_code == 200, manual.text
    assert (
        await client.post(f"/api/schedules/{schedule_id}/pause", headers=headers)
    ).status_code == 200
    assert (
        await client.post(f"/api/schedules/{schedule_id}/resume", headers=headers)
    ).status_code == 200
    async with container.session_factory() as session:
        current = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(edition.job_id)
    assert current is not None and current.workflow is EditionWorkflow.PAUSED
    assert current.safe_reason == "operator_paused"
    assert job is not None and job.status == "paused"


async def test_pause_is_scoped_and_rolls_back_on_late_session_expiry(
    client, container, user
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    created = await client.post(
        "/api/schedules", json={"name": "Scoped", "template_id": "intsum"}, headers=headers
    )
    assert created.status_code == 201, created.text
    schedule_id = created.json()["id"]
    outsider = await create_user(
        container, email="activation-outsider@example.com", password="another-long-passphrase"
    )
    outsider_headers = bearer(await login_token(client, outsider.email, "another-long-passphrase"))
    assert (
        await client.post(f"/api/schedules/{schedule_id}/pause", headers=outsider_headers)
    ).status_code == 404
    original = Auditor.record

    async def delayed(self, action, **kwargs):
        result = await original(self, action, **kwargs)
        if kwargs.get("details", {}).get("action") == "pause":
            container.clock.advance(timedelta(days=1))
        return result

    with patch.object(Auditor, "record", delayed):
        response = await client.post(f"/api/schedules/{schedule_id}/pause", headers=headers)
    assert response.status_code == 401
    async with container.session_factory() as session:
        stored = await container.repositories(session).schedules.get(UUID(schedule_id))
    assert stored is not None and stored.enabled is True


async def test_team_schedule_controls_require_current_write_authority(
    client, container, user, admin
) -> None:
    member = await create_user(
        container, email="activation-member@example.com", password="another-long-passphrase"
    )
    manager = await create_user(
        container,
        email="activation-manager@example.com",
        password="another-long-passphrase",
        role=Role.MANAGER,
    )
    async with team_service(container) as service:
        team = await service.create(admin, "Activation team", CONTEXT)
        for teammate, role in (
            (user, MembershipRole.MEMBER),
            (member, MembershipRole.MEMBER),
            (manager, MembershipRole.MANAGER),
        ):
            await service.set_member(
                admin, team.id, email=teammate.email, role=role, context=CONTEXT
            )
    owner_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    created = await client.post(
        "/api/schedules",
        json={"name": "Team cadence", "template_id": "intsum", "team_id": str(team.id)},
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    path = f"/api/schedules/{created.json()['id']}"
    member_headers = bearer(await login_token(client, member.email, "another-long-passphrase"))
    assert (await client.post(f"{path}/pause", headers=member_headers)).status_code == 403
    manager_headers = bearer(await login_token(client, manager.email, "another-long-passphrase"))
    paused = await client.post(f"{path}/pause", headers=manager_headers)
    assert paused.status_code == 200 and paused.json()["enabled"] is False
    resumed = await client.post(f"{path}/resume", headers=owner_headers)
    assert resumed.status_code == 200 and resumed.json()["enabled"] is True

"""Deleting a subscription retains its private audit graph and stops future work."""

from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.selected_index_models import SelectedIndexLossRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionRow,
    SubscriptionRevisionRow,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.auditing import Auditor
from ase.container.subscription_enqueue import SubscriptionAdmission
from ase.domain.audit import AuditAction
from ase.domain.subscription_editions import EditionWorkflow
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE


async def _enable_sqlite_foreign_keys(container) -> None:
    if container.engine.dialect.name != "sqlite":
        return  # PostgreSQL enforces the same FK graph without a pragma.
    async with container.engine.connect() as connection:
        await connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert await connection.scalar(text("PRAGMA foreign_keys")) == 1
        await connection.commit()


async def test_delete_tombstones_and_retains_revision_edition_and_selected_index(
    client, container, user
) -> None:
    await _enable_sqlite_foreign_keys(container)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/schedules",
        json={"name": "Retain private history", "template_id": "intsum", "enabled": True},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    schedule_id = UUID(created.json()["id"])
    due = container.clock.now() + timedelta(days=1)
    edition_id = uuid4()
    pending_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            SubscriptionRevisionRow(
                subscription_id=schedule_id,
                revision=1,
                owner_id=user.id,
                team_id=None,
                request_snapshot="{}",
                compatibility_fingerprint="a" * 64,
                recurrence_policy="local_iana_v1",
                collection_policy="rolling_snapshot_v1",
                enabled=True,
                created_at=container.clock.now(),
            )
        )
        await session.flush()
        session.add(
            SubscriptionEditionRow(
                id=edition_id,
                subscription_id=schedule_id,
                trigger="scheduled",
                due_at_utc=due,
                request_uuid=None,
                frozen_revision=1,
                requested_start=due - timedelta(days=1),
                requested_end=due,
                effective_intervals=[],
                gaps=[],
                compatibility_fingerprint="a" * 64,
                workflow="skipped",
                report_quality="absent",
                coverage="unknown",
                safe_reason="not_run",
                created_at=container.clock.now(),
                updated_at=container.clock.now(),
                revision=1,
                accepted_as_baseline=False,
            )
        )
        session.add(
            SubscriptionEditionRow(
                id=pending_id,
                subscription_id=schedule_id,
                trigger="scheduled",
                due_at_utc=due + timedelta(days=1),
                request_uuid=None,
                frozen_revision=1,
                requested_start=due,
                requested_end=due + timedelta(days=1),
                effective_intervals=[],
                gaps=[],
                compatibility_fingerprint="a" * 64,
                workflow="pending",
                report_quality="absent",
                coverage="unknown",
                created_at=container.clock.now(),
                updated_at=container.clock.now(),
                revision=1,
                accepted_as_baseline=False,
            )
        )
        session.add(
            SelectedIndexLossRow(
                subscription_id=schedule_id,
                owner_id=user.id,
                team_id=None,
                source_id="reviewed-source",
                reason="retention_expired",
                lost_items=1,
                earliest_event_at=container.clock.now(),
                latest_event_at=container.clock.now(),
                occurred_at=container.clock.now(),
            )
        )
        await session.commit()

    deleted = await client.delete(f"/api/schedules/{schedule_id}", headers=bearer(token))
    assert deleted.status_code == 204, deleted.text
    assert (
        await client.delete(f"/api/schedules/{schedule_id}", headers=bearer(token))
    ).status_code == 204
    listed = await client.get("/api/schedules", headers=bearer(token))
    assert listed.status_code == 200 and listed.json()["items"] == []
    history = await client.get(f"/api/schedules/{schedule_id}/editions", headers=bearer(token))
    assert history.status_code == 200
    assert {item["id"] for item in history.json()["items"]} == {str(edition_id), str(pending_id)}

    async with container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule_id)
        assert row is not None and not row.enabled and row.archived_at is not None
        assert await session.get(SubscriptionRevisionRow, (schedule_id, 1)) is not None
        assert await session.get(SubscriptionEditionRow, edition_id) is not None
        pending = await SqlSubscriptionEditionRepository(session).get(pending_id)
        assert pending is not None and pending.workflow is EditionWorkflow.CANCELLED
        losses = await session.scalars(
            select(SelectedIndexLossRow).where(SelectedIndexLossRow.subscription_id == schedule_id)
        )
        assert len(list(losses)) == 1
        assert await SqlSubscriptionEditionRepository(session).get(edition_id) is not None
    assert await SubscriptionAdmission(container).tick() == 0


@pytest.mark.parametrize("path", ["pause", "resume"])
async def test_archived_schedule_cannot_be_reactivated(client, container, user, path: str) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/schedules",
        json={"name": "Archived", "template_id": "intsum"},
        headers=bearer(token),
    )
    assert created.status_code == 201
    schedule_id = created.json()["id"]
    assert (
        await client.delete(f"/api/schedules/{schedule_id}", headers=bearer(token))
    ).status_code == 204
    response = await client.post(f"/api/schedules/{schedule_id}/{path}", headers=bearer(token))
    assert response.status_code == 404
    updated = await client.put(
        f"/api/schedules/{schedule_id}",
        json={"name": "Revived", "template_id": "intsum", "enabled": True},
        headers=bearer(token),
    )
    assert updated.status_code == 404
    manual = await client.post(
        f"/api/schedules/{schedule_id}/run-now",
        json={"request_id": str(uuid4())},
        headers=bearer(token),
    )
    assert manual.status_code == 404


async def test_archive_requires_current_owner_authority(client, container, user) -> None:
    owner_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    created = await client.post(
        "/api/schedules",
        json={"name": "Private", "template_id": "intsum"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    schedule_id = UUID(created.json()["id"])
    outsider = await create_user(
        container, email="archive-outsider@example.com", password="another-long-passphrase"
    )
    outsider_headers = bearer(await login_token(client, outsider.email, "another-long-passphrase"))
    denied = await client.delete(f"/api/schedules/{schedule_id}", headers=outsider_headers)
    assert denied.status_code == 404
    async with container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule_id)
        assert row is not None and row.enabled and row.archived_at is None


async def test_archive_rolls_back_when_session_expires_before_commit(
    client, container, user
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    created = await client.post(
        "/api/schedules",
        json={"name": "Session fence", "template_id": "intsum"},
        headers=headers,
    )
    assert created.status_code == 201
    schedule_id = UUID(created.json()["id"])
    original = Auditor.record

    async def expire(self, action, **kwargs):
        result = await original(self, action, **kwargs)
        if action is AuditAction.SCHEDULE_DELETED:
            container.clock.advance(timedelta(days=1))
        return result

    with patch.object(Auditor, "record", expire):
        response = await client.delete(f"/api/schedules/{schedule_id}", headers=headers)
    assert response.status_code == 401
    async with container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule_id)
        assert row is not None and row.enabled and row.archived_at is None


@pytest.mark.parametrize("running", [False, True])
async def test_archive_cancels_active_edition_and_blocks_generic_resume(
    client, container, user, running: bool
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    created = await client.post(
        "/api/schedules",
        json={"name": "Queued archive", "template_id": "intsum", "country_iso": "UA"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    schedule_id = UUID(created.json()["id"])
    container.clock.advance(
        datetime.fromisoformat(created.json()["next_run_at"])
        - container.clock.now()
        + timedelta(minutes=1)
    )
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        edition = await ledger.active(schedule_id)
        assert edition is not None and edition.job_id is not None
        job_id = edition.job_id
        if running:
            jobs = SqlReportJobRepository(session)
            job = await jobs.get(job_id)
            assert job is not None
            claimed = await jobs.claim(
                job.id,
                expected_revision=job.revision,
                lease_token=uuid4(),
                now=container.clock.now(),
                lease_until=container.clock.now() + timedelta(seconds=45),
            )
            assert claimed is not None
            edition = await ledger.advance(
                replace(
                    edition,
                    workflow=EditionWorkflow.RUNNING,
                    updated_at=container.clock.now(),
                    revision=edition.revision + 1,
                ),
                expected_revision=edition.revision,
            )
            assert edition is not None
            await session.commit()
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (
        await client.delete(f"/api/schedules/{schedule_id}", headers=headers)
    ).status_code == 204
    async with container.session_factory() as session:
        archived_edition = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(job_id)
        assert archived_edition is not None
        assert archived_edition.workflow is EditionWorkflow.CANCELLED
        assert archived_edition.safe_reason == "subscription_archived"
        assert job is not None and job.status == "paused"
    assert (
        await client.post(f"/api/report-jobs/{job_id}/resume", headers=headers)
    ).status_code == 422
    assert (await client.get(f"/api/report-jobs/{job_id}", headers=headers)).status_code == 200
    assert await container.schedule_runner.run_once() == 0

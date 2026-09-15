"""Explicit partial baselines retain gaps and require saved edition provenance."""

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.models import AuditLogRow, ReportVersionRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.report_jobs import ReportJob
from ase.domain.reports import ReportStatus
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
)
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from report_documents_helpers import document_records


async def _published(client, container, headers, *, quality=EditionQuality.NEEDS_REVIEW):
    created = await client.post(
        "/api/schedules",
        json={"name": "Analytical baseline", "template_id": "intsum", "country_iso": "UA"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    schedule_id = UUID(created.json()["id"])
    async with container.session_factory() as session:
        schedule = await container.repositories(session).schedules.get(schedule_id)
        assert schedule is not None
        revision = revision_from_schedule(schedule, 1)
        ledger = SqlSubscriptionEditionRepository(session)
        await ledger.add_revision(revision)
        requested = ObservationInterval(
            schedule.next_run_at - timedelta(days=1), schedule.next_run_at
        )
        edition = await ledger.reserve(
            SubscriptionEdition(
                id=uuid4(),
                subscription_id=schedule_id,
                trigger=EditionTrigger.SCHEDULED,
                due_at_utc=schedule.next_run_at,
                request_uuid=None,
                frozen_revision=1,
                requested=requested,
                effective_intervals=(),
                gaps=(requested,),
                compatibility_fingerprint=revision.compatibility_fingerprint,
                baseline_version_id=None,
                workflow=EditionWorkflow.PENDING,
                report_quality=EditionQuality.ABSENT,
                coverage=EditionCoverage.UNKNOWN,
                created_at=container.clock.now(),
                updated_at=container.clock.now(),
            )
        )
        report, version = document_records(schedule.created_by)
        status = (
            ReportStatus.NEEDS_REVIEW
            if quality is EditionQuality.NEEDS_REVIEW
            else ReportStatus.READY
        )
        report = replace(
            report,
            status=status,
            scope=report_scope(request_from_revision(revision), TEMPLATES[schedule.template_id]),
            period_from=requested.start,
            period_to=requested.end,
            data_cutoff=requested.end,
            team_id=schedule.team_id,
        )
        version = replace(
            version,
            status=status,
            period_from=requested.start,
            period_to=requested.end,
            data_cutoff=requested.end,
        )
        await container.repositories(session).reports.add(report, version)
        job = ReportJob(
            id=uuid4(),
            request_key=edition.job_request_key,
            owner_id=schedule.created_by,
            team_id=schedule.team_id,
            title=report.title,
            status="needs_review" if quality is EditionQuality.NEEDS_REVIEW else "completed",
            stage="completed",
            created_at=container.clock.now(),
            updated_at=container.clock.now(),
            payload={"schema_version": 1, "summary": {}},
            report_id=report.id,
            version_id=version.id,
        )
        await SqlReportJobRepository(session).add(job)
        saved = await ledger.advance(
            replace(
                edition,
                workflow=EditionWorkflow.COMPLETED,
                report_quality=quality,
                coverage=EditionCoverage.PARTIAL,
                report_id=report.id,
                version_id=version.id,
                job_id=job.id,
                revision=edition.revision + 1,
            ),
            expected_revision=edition.revision,
        )
        assert saved is not None
        await session.commit()
    return schedule_id, saved, report, version


@pytest.mark.parametrize("quality", [EditionQuality.NEEDS_REVIEW, EditionQuality.READY])
async def test_accept_baseline_is_audited_once_without_covering_gaps(
    client, container, user, quality
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    schedule_id, edition, _, version = await _published(client, container, headers, quality=quality)
    prior = ObservationInterval(
        edition.requested.start - timedelta(days=1), edition.requested.start
    )
    async with container.session_factory() as session:
        await SqlSubscriptionEditionRepository(session).save_lineage(
            SubscriptionLineage(
                subscription_id=schedule_id,
                compatibility_fingerprint=edition.compatibility_fingerprint,
                analytical_baseline_version_id=None,
                covered_intervals=(prior,),
                complete_cutoff=prior.end,
                updated_at=container.clock.now(),
            ),
            expected_revision=None,
        )
        await session.commit()

    path = f"/api/schedules/{schedule_id}/editions/{edition.id}/accept-baseline"
    accepted = await client.post(path, headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.headers["cache-control"] == "private, no-store"
    assert accepted.json()["analytical_baseline_version_id"] == str(version.id)
    assert datetime.fromisoformat(accepted.json()["complete_cutoff"]) == prior.end
    repeated = await client.post(path, headers=headers)
    assert repeated.status_code == 200 and repeated.json() == accepted.json()
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        lineage = await ledger.get_lineage(schedule_id)
        stored = await ledger.get(edition.id)
        audits = list(
            await session.scalars(
                select(AuditLogRow).where(AuditLogRow.subject == str(schedule_id))
            )
        )
    assert lineage is not None and lineage.covered_intervals == (prior,)
    assert lineage.complete_cutoff == prior.end
    assert stored is not None and stored.gaps == (edition.requested,)
    assert stored.accepted_as_baseline is True
    assert len([row for row in audits if row.details.get("action") == "accept_baseline"]) == 1
    history = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["accepted_as_baseline"] is True


async def test_accept_baseline_rejects_outsider_wrong_schedule_and_failed_version(
    client, container, user
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    schedule_id, edition, _, version = await _published(client, container, headers)
    path = f"/api/schedules/{schedule_id}/editions/{edition.id}/accept-baseline"
    other = await create_user(
        container, email="baseline-outsider@example.com", password="another-long-passphrase"
    )
    outsider = bearer(await login_token(client, other.email, "another-long-passphrase"))
    assert (await client.post(path, headers=outsider)).status_code == 404
    assert (
        await client.post(
            f"/api/schedules/{uuid4()}/editions/{edition.id}/accept-baseline", headers=headers
        )
    ).status_code == 404
    async with container.session_factory() as session:
        await session.execute(
            update(ReportVersionRow)
            .where(ReportVersionRow.id == version.id)
            .values(status=ReportStatus.FAILED.value)
        )
        await session.commit()
    assert (await client.post(path, headers=headers)).status_code == 409
    async with container.session_factory() as session:
        assert await SqlSubscriptionEditionRepository(session).get_lineage(schedule_id) is None


async def test_accept_baseline_creates_analytical_lineage_without_coverage(
    client, container, user
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    schedule_id, edition, _, version = await _published(client, container, headers)
    path = f"/api/schedules/{schedule_id}/editions/{edition.id}/accept-baseline"
    accepted = await client.post(path, headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["analytical_baseline_version_id"] == str(version.id)
    assert accepted.json()["covered_intervals"] == []
    assert accepted.json()["complete_cutoff"] is None
    assert (await client.post(path, headers=headers)).json() == accepted.json()
    history = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["accepted_as_baseline"] is True


async def test_accept_baseline_rejects_changed_definition(client, container, user) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    schedule_id, edition, _, _ = await _published(client, container, headers)
    changed = await client.put(
        f"/api/schedules/{schedule_id}",
        json={
            "name": "Changed scope",
            "template_id": "intsum",
            "country_iso": "GB",
        },
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    path = f"/api/schedules/{schedule_id}/editions/{edition.id}/accept-baseline"
    assert (await client.post(path, headers=headers)).status_code == 409
    async with container.session_factory() as session:
        assert await SqlSubscriptionEditionRepository(session).get_lineage(schedule_id) is None

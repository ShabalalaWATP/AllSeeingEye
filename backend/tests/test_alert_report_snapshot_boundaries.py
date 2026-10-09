"""Strict snapshot identity, safe legacy behaviour and unchanged normal request identity."""

import hashlib
import json
from dataclasses import asdict

import pytest
from sqlalchemy import update

from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.report_job_codec import payload_columns
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.application.dto import RequestContext
from ase.application.report_jobs.controls import request_digest
from ase.application.reports.request import ReportRequest
from ase.container.alert_reports import AlertReportAdmission
from ase.domain.errors import InvalidRequest
from report_job_api_helpers import job_settings, prepared, stored, work
from test_alert_report_queue import current_alert, rule

__all__ = ["job_settings"]


def test_existing_manual_request_identity_does_not_change():
    request = ReportRequest("intsum")
    historical = asdict(request)
    historical.pop("alert_origin")
    encoded = json.dumps(historical, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert request_digest(request) == hashlib.sha256(encoded.encode()).hexdigest()


async def test_missing_legacy_snapshot_never_recollects_live_evidence(container, client, user):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    async with container.session_factory() as session:
        await session.execute(
            update(AlertRow).where(AlertRow.id == alert.id).values(report_snapshot=None)
        )
        await session.commit()
    await AlertReportAdmission(container).tick()
    current = await current_alert(container, alert.id)
    assert current.report_status == "failed" and current.report_error == "evidence_unavailable"
    assert current.report_job_id is None and not gateway.calls


async def test_legacy_queued_job_without_origin_stops_before_paid_work(container, client, user):
    gateway, headers = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    queued = await current_alert(container, alert.id)
    job = await stored(container, queued.report_job_id)
    job.payload["input"]["scope"].pop("alert_origin")
    async with container.session_factory() as session:
        await session.execute(
            update(ReportJobRow)
            .where(ReportJobRow.id == job.id)
            .values(**payload_columns(job.payload))
        )
        await session.commit()
    await work(container)
    current = await current_alert(container, alert.id)
    assert current.report_status == "paused" and current.report_error == "invalid_snapshot"
    assert current.report_id is None and not gateway.calls
    response = await client.get(f"/api/report-jobs/{job.id}", headers=headers)
    assert response.status_code == 200 and not response.json()["can_resume"]


async def test_manual_regeneration_cannot_silently_replace_alert_evidence(container, client, user):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    await work(container)
    completed = await current_alert(container, alert.id)
    calls = len(gateway.calls)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="original frozen evidence"):
            await container.generate_report(session).regenerate(
                user, completed.report_id, RequestContext()
            )
    assert len(gateway.calls) == calls


async def test_unsupported_country_sets_are_rejected_at_rule_creation(container, user):
    with pytest.raises(InvalidRequest, match="at most eight countries"):
        await rule(
            container, user, countries=("UA", "PL", "DE", "FR", "US", "GB", "ES", "PT", "IT")
        )

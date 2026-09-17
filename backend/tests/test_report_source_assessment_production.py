"""Actual production captures source provenance using controlled, local stages."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.reports.document import build_document
from ase.application.reports.drafting import Draft
from ase.application.reports.production import Producer
from ase.application.reports.production_types import Totals
from ase.application.reports.production_version import build_version
from ase.application.reports.selection import Selection
from ase.application.reports.source_assessment_projection import capture_unassessed_report_sources
from ase.domain.events import Credibility, Reliability
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.reports import ReportBody, ReportStatus
from production_integration_helpers import (
    BarrierResolver,
    RecordingUsage,
    StageGateway,
    production_job,
    production_record,
)
from report_helpers import filled_store
from source_projection_helpers import BODY, EVIDENCE


async def test_final_production_capture_is_saved_before_usage_without_grade_promotion(
    container, user
):
    job = replace(production_job(user, container.cipher), version_id=uuid4())
    usage, gateway = RecordingUsage(), StageGateway()
    seen = []

    class Projector:
        async def build(self, record, version):
            assert gateway.calls == [
                "direction",
                "report",
                "advocacy",
                "report_analysis",
                "entailment",
            ]
            assert usage.rows == []
            seen.append(version.source_assessment)
            return build_document(record, version)

    async def profile_for(role):
        return job.profile

    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=gateway,
        usage=usage,
        url_resolver=BarrierResolver(),
        projector=Projector(),
    )
    version = await producer.produce(job, profile_for)
    capture = version.source_assessment
    assert seen == [capture]
    assert capture.status == "captured"
    assert capture.report_version_id == version.id == job.version_id
    assert capture.projection.assessments
    assert {row.subject for row in capture.projection.claims} == {"unassessed"}
    assert all(
        row.reliability is Reliability.F and row.credibility is Credibility.CANNOT_BE_JUDGED
        for row in capture.projection.assessments
    )
    assert version.assessment == build_report_assessment(
        version.body, version.evidence, version.findings
    )
    assert capture == capture_unassessed_report_sources(
        version.id, version.body, version.evidence, frozen_at=version.data_cutoff
    )
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.add(production_record(job, version), replace(version, profile_id=None))
        await session.commit()
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(version.report_id, 1)
    assert saved.source_assessment == capture
    assert saved.evidence == version.evidence
    assert saved.body == version.body


@pytest.mark.parametrize("failed", [False, True])
async def test_failed_or_uncited_draft_is_retained_with_honest_metadata(container, user, failed):
    job = production_job(user, container.cipher)
    body = (
        ReportBody()
        if failed
        else replace(
            BODY, key_judgements=(replace(BODY.key_judgements[0], supporting_evidence=("E999",)),)
        )
    )
    version = await build_version(
        job,
        Draft(body=None if failed else body),
        body,
        Selection(EVIDENCE, 0, 1),
        Totals(),
        direction=None,
        receipt=None,
        advocacy=None,
        challenge=None,
        url_resolver=None,
        progress=None,
    )
    assert version.status is (ReportStatus.FAILED if failed else ReportStatus.NEEDS_REVIEW)
    capture = version.source_assessment
    if failed:
        assert capture.status == "captured"
        assert capture.projection.claims == capture.projection.assessments == ()
    else:
        assert capture.status == "unavailable"
        assert capture.projection is None and capture.reason
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.add(production_record(job, version), replace(version, profile_id=None))
        await session.commit()
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(version.report_id, 1)
    assert saved.source_assessment == capture
    assert saved.evidence == EVIDENCE


async def test_source_capture_cutoff_includes_evidence_collected_after_job_start(container, user):
    job = production_job(user, container.cipher)
    later = job.now + timedelta(minutes=10)
    evidence = (replace(EVIDENCE[0], captured_at=later),)
    version = await build_version(
        job,
        Draft(body=BODY),
        BODY,
        Selection(evidence, 0, 1),
        Totals(),
        direction=None,
        receipt=None,
        advocacy=None,
        challenge=None,
        url_resolver=None,
        progress=None,
    )
    assert version.source_assessment.status == "captured"
    assert version.source_assessment.frozen_at == later == version.data_cutoff
    assert version.created_at == job.now

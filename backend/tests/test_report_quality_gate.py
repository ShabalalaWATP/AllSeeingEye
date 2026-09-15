"""Release status follows frozen material review findings, not draft validity alone."""

from dataclasses import replace

from ase.application.reports.drafting import Draft
from ase.application.reports.production_types import Totals
from ase.application.reports.production_version import build_version
from ase.application.reports.quality_gate import final_report_status, material_review_reasons
from ase.application.reports.selection import Selection
from ase.domain.citation_checks import CitationStatus, JudgementCitationCheck, ReportCitationChecks
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.reports import ReportStatus
from production_integration_helpers import production_job
from report_documents_helpers import document_records
from test_challenge_integration import challenge_records


def test_missing_support_and_source_context_prevent_ready_release() -> None:
    _, version = challenge_records()
    assessment = build_report_assessment(version.body, version.evidence, ())
    assessment = replace(
        assessment,
        judgements=(replace(assessment.judgements[0], status="unsupported"),),
    )
    checks = ReportCitationChecks(
        "frozen-check-v1",
        (JudgementCitationCheck("KJ1", CitationStatus.CONTEXT_INSUFFICIENT, (), ()),),
    )
    reasons = material_review_reasons(assessment, checks, version.challenge)
    assert "At least one key judgement lacks assessable supporting evidence." in reasons
    assert "A key judgement has insufficient original source context." in reasons
    assert (
        final_report_status(ReportStatus.READY, assessment, checks, version.challenge)
        is ReportStatus.NEEDS_REVIEW
    )


def test_incomplete_challenge_and_literal_mismatch_require_review() -> None:
    _, version = challenge_records()
    challenge = replace(
        version.challenge,
        reviews=(replace(version.challenge.reviews[0], status="invalid"),),
    )
    checks = ReportCitationChecks(
        "frozen-check-v1",
        (JudgementCitationCheck("KJ1", CitationStatus.REVIEW_REQUIRED, (), ()),),
    )
    assert (
        final_report_status(ReportStatus.READY, None, checks, challenge)
        is ReportStatus.NEEDS_REVIEW
    )
    assert "A planned challenge review was not completed." in material_review_reasons(
        None, checks, challenge
    )


def test_failed_release_is_not_promoted_and_clean_checks_do_not_downgrade() -> None:
    checks = ReportCitationChecks(
        "frozen-check-v1",
        (JudgementCitationCheck("KJ1", CitationStatus.EXCERPT_PRESENT, (), ()),),
    )
    assert final_report_status(ReportStatus.FAILED, None, checks, None) is ReportStatus.FAILED
    assert final_report_status(ReportStatus.READY, None, checks, None) is ReportStatus.READY


async def test_production_freezes_review_status_after_literal_checks(container, user) -> None:
    _, sample = document_records(user.id)
    evidence = tuple(replace(item, summary="") for item in sample.evidence)
    job = production_job(user, container.cipher)
    version = await build_version(
        job,
        Draft(body=sample.body),
        sample.body,
        Selection(evidence, 0, len(evidence)),
        Totals(),
        direction=None,
        receipt=None,
        advocacy=None,
        challenge=None,
        url_resolver=None,
        progress=None,
    )
    assert version.status is ReportStatus.NEEDS_REVIEW
    assert version.document_schema_version == 2
    assert "A key judgement has insufficient original source context." in version.markdown

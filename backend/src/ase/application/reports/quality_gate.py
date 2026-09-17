"""Conservative automated release decision from frozen assessment components."""

from __future__ import annotations

from collections.abc import Sequence

from ase.domain.challenge import ReportChallenge
from ase.domain.citation_checks import CitationStatus, ReportCitationChecks
from ase.domain.evidence_matrix import ReportAssessment
from ase.domain.report_quality_rules import MAX_REVIEW_REASONS, REVIEW_RULES
from ase.domain.reports import ReportStatus
from ase.domain.validation_types import Finding, Severity


def _mechanical_reasons(findings: Sequence[Finding]) -> list[str]:
    """One plain reason per failed post-draft check, in the order the checks ran."""
    return list(
        dict.fromkeys(
            finding.message
            for finding in findings
            if finding.rule in REVIEW_RULES and finding.severity is Severity.ERROR
        )
    )[:MAX_REVIEW_REASONS]


def material_review_reasons(
    assessment: ReportAssessment | None,
    citation_checks: ReportCitationChecks | None,
    challenge: ReportChallenge | None,
    findings: Sequence[Finding] = (),
) -> tuple[str, ...]:
    """Return visible reasons without equating literal matching with factual verification."""
    reasons: list[str] = []
    if assessment is not None:
        if any(row.status == "unsupported" for row in assessment.judgements):
            reasons.append("At least one key judgement lacks assessable supporting evidence.")
        if any(row.balance == "opposition_at_least_as_strong" for row in assessment.judgements):
            reasons.append("Contrary reporting is at least as strong as stated support.")
    if citation_checks is not None:
        statuses = {row.status for row in citation_checks.judgements}
        if CitationStatus.ABSENT in statuses:
            reasons.append("A key judgement has a missing supporting source or citation.")
        if CitationStatus.CONTEXT_INSUFFICIENT in statuses:
            reasons.append("A key judgement has insufficient original source context.")
        if CitationStatus.REVIEW_REQUIRED in statuses:
            reasons.append("A key judgement has a literal source mismatch to review.")
    if challenge is not None and any(row.status != "completed" for row in challenge.reviews):
        reasons.append("A planned challenge review was not completed.")
    reasons.extend(_mechanical_reasons(findings))
    return tuple(dict.fromkeys(reasons))


def final_report_status(
    base_status: ReportStatus,
    assessment: ReportAssessment | None,
    citation_checks: ReportCitationChecks | None,
    challenge: ReportChallenge | None,
    findings: Sequence[Finding] = (),
) -> ReportStatus:
    if base_status is ReportStatus.FAILED:
        return base_status
    if base_status is ReportStatus.NEEDS_REVIEW or material_review_reasons(
        assessment, citation_checks, challenge, findings
    ):
        return ReportStatus.NEEDS_REVIEW
    return ReportStatus.READY

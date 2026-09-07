"""Revalidate retained identity decisions against their exact frozen source evidence."""

from ase.domain.claim_revisions import ClaimCitationInput, freeze_claim_citations
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.identity_review import (
    IdentityDecisionRevision,
    freeze_identity_candidate,
    validate_identity_revision,
)
from ase.domain.identity_roots import IdentityDecisionRoot
from ase.domain.report_records import ReportRecord, ReportVersion


def identity_subject(report: ReportRecord) -> str:
    subject = report.scope.get("research_subject")
    if (
        report.scope.get("research_focus") != "company"
        or not isinstance(subject, str)
        or not subject.strip()
        or len(subject) > 300
    ):
        raise InvalidRequest("Identity review requires an explicit company research subject.")
    return subject


def validate_retained_identity(
    root: IdentityDecisionRoot, version: ReportVersion, value: IdentityDecisionRevision
) -> None:
    try:
        validate_identity_revision(value)
        if (
            value.decision_id != root.id
            or value.report_id != root.report_id
            or value.report_version_id != root.report_version_id
            or value.subject != root.subject
            or value.candidate.candidate.evidence_label != root.candidate_label
            or value.created_at < root.created_at
            or freeze_identity_candidate(version, root.candidate_label) != value.candidate
        ):
            raise ValueError("Identity anchor mismatch")
        inputs = tuple(
            ClaimCitationInput(
                row.label,
                row.relation,
                row.excerpt.field,
                row.excerpt.start,
                row.excerpt.end,
                row.excerpt.text,
            )
            for row in value.citations
        )
        if inputs and freeze_claim_citations(version, inputs) != value.citations:
            raise ValueError("Identity citation mismatch")
    except ValueError as exc:
        raise Conflict("Identity history no longer matches its frozen evidence.") from exc

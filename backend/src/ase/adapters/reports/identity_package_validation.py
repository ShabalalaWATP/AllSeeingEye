"""Offline identity export validation, separate from the caller's access checks."""

from ase.application.reports.identity_integrity import identity_subject
from ase.domain.claim_revisions import ClaimCitationInput, freeze_claim_citations
from ase.domain.errors import InvalidRequest
from ase.domain.identity_review import (
    IdentityDecisionRevision,
    freeze_identity_candidate,
    validate_identity_revision,
)
from ase.domain.report_records import ReportRecord, ReportVersion


def validate_identity_selection(
    record: ReportRecord, version: ReportVersion, revisions: tuple[IdentityDecisionRevision, ...]
) -> None:
    if not isinstance(revisions, tuple) or len(revisions) > 20:
        raise InvalidRequest("Select at most twenty exact identity revisions.")
    if not revisions:
        return
    subject = identity_subject(record)
    if len({row.id for row in revisions}) != len(revisions):
        raise InvalidRequest("An identity revision can only be selected once.")
    for row in revisions:
        try:
            validate_identity_revision(row)
            if (
                row.report_id != version.report_id
                or row.report_version_id != version.id
                or row.subject != subject
                or row.candidate
                != freeze_identity_candidate(version, row.candidate.candidate.evidence_label)
            ):
                raise ValueError("Selected identity has a different evidence anchor")
            citations = tuple(
                ClaimCitationInput(
                    item.label,
                    item.relation,
                    item.excerpt.field,
                    item.excerpt.start,
                    item.excerpt.end,
                    item.excerpt.text,
                )
                for item in row.citations
            )
            if citations and freeze_claim_citations(version, citations) != row.citations:
                raise ValueError("Selected identity citations differ from captured evidence")
        except ValueError as exc:
            raise InvalidRequest(
                "Selected identities do not match frozen report evidence."
            ) from exc

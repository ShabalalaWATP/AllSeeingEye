"""Offline relationship export validation, separate from the caller's access checks."""

from ase.domain.claim_revisions import ClaimCitationInput, freeze_claim_citations
from ase.domain.errors import InvalidRequest
from ase.domain.relationship_assertions import freeze_relationship_assertion
from ase.domain.relationship_review import (
    RelationshipReviewRevision,
    validate_relationship_revision,
)
from ase.domain.report_records import ReportRecord, ReportVersion


def validate_relationship_selection(
    record: ReportRecord, version: ReportVersion, revisions: tuple[RelationshipReviewRevision, ...]
) -> None:
    if not isinstance(revisions, tuple) or len(revisions) > 20:
        raise InvalidRequest("Select at most twenty exact relationship revisions.")
    if not revisions:
        return
    if record.id != version.report_id:
        raise InvalidRequest("The selected relationship parent report differs.")
    if len({row.id for row in revisions}) != len(revisions):
        raise InvalidRequest("A relationship revision can only be selected once.")
    for row in revisions:
        try:
            validate_relationship_revision(row)
            if (
                row.report_id != version.report_id
                or row.report_version_id != version.id
                or row.assertion
                != freeze_relationship_assertion(version, row.assertion.evidence_label)
            ):
                raise ValueError("Selected relationship has a different evidence anchor")
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
                raise ValueError("Selected relationship citations differ from captured evidence")
        except ValueError as exc:
            raise InvalidRequest(
                "Selected relationships do not match frozen report evidence."
            ) from exc

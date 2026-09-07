"""Revalidate retained relationship decisions against their exact frozen source evidence."""

from ase.domain.claim_revisions import ClaimCitationInput, freeze_claim_citations
from ase.domain.errors import Conflict
from ase.domain.relationship_assertions import freeze_relationship_assertion
from ase.domain.relationship_review import (
    RelationshipReviewRevision,
    validate_relationship_revision,
)
from ase.domain.relationship_roots import RelationshipReviewRoot
from ase.domain.report_records import ReportVersion


def validate_retained_relationship(
    root: RelationshipReviewRoot, version: ReportVersion, value: RelationshipReviewRevision
) -> None:
    try:
        validate_relationship_revision(value)
        if (
            value.relationship_id != root.id
            or value.report_id != root.report_id
            or value.report_version_id != root.report_version_id
            or value.assertion.evidence_label != root.evidence_label
            or value.created_at < root.created_at
            or freeze_relationship_assertion(version, root.evidence_label) != value.assertion
        ):
            raise ValueError("Relationship anchor mismatch")
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
            raise ValueError("Relationship citation mismatch")
    except ValueError as exc:
        raise Conflict("Relationship history no longer matches its frozen evidence.") from exc

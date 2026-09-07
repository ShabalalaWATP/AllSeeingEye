"""Attributed assessment revisions of exact source-reported relationship assertions."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.claim_revisions import (
    ClaimCitation,
    ClaimCitationInput,
    _validate_frozen_citations,
    freeze_claim_citations,
)
from ase.domain.relationship_assertions import (
    RelationshipAssertionSnapshot,
    freeze_relationship_assertion,
    validate_relationship_assertion,
)
from ase.domain.report_records import ReportVersion


class RelationshipDisposition(StrEnum):
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    UNRESOLVED = "unresolved"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True, slots=True)
class RelationshipReviewRevision:
    id: UUID
    relationship_id: UUID
    report_id: UUID
    report_version_id: UUID
    number: int
    previous_id: UUID | None
    assertion: RelationshipAssertionSnapshot
    disposition: RelationshipDisposition
    rationale: str
    unresolved_conflicts: tuple[str, ...]
    citations: tuple[ClaimCitation, ...]
    authored_by: UUID
    created_at: datetime


def _text(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 1200:
        raise ValueError("Relationship review text is empty or oversized")
    value.encode("utf-8")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("Relationship review text contains invalid control characters")


def validate_relationship_revision(value: RelationshipReviewRevision) -> None:
    if not isinstance(value, RelationshipReviewRevision):
        raise ValueError("Invalid relationship revision")
    for identity in (
        value.id,
        value.relationship_id,
        value.report_id,
        value.report_version_id,
        value.authored_by,
    ):
        if not isinstance(identity, UUID):
            raise ValueError("Invalid relationship review identifier")
    if type(value.number) is not int or not 1 <= value.number <= 100:
        raise ValueError("Invalid relationship revision number")
    if not isinstance(value.disposition, RelationshipDisposition):
        raise ValueError("Invalid relationship disposition")
    if value.number == 1:
        if value.previous_id is not None or value.disposition is RelationshipDisposition.WITHDRAWN:
            raise ValueError("An initial relationship review cannot be withdrawn")
    elif not isinstance(value.previous_id, UUID) or value.previous_id == value.id:
        raise ValueError("Invalid relationship revision predecessor")
    if not isinstance(value.created_at, datetime) or value.created_at.utcoffset() is None:
        raise ValueError("Invalid relationship review timestamp")
    _text(value.rationale)
    if not isinstance(value.unresolved_conflicts, tuple) or len(value.unresolved_conflicts) > 20:
        raise ValueError("Invalid relationship disagreement collection")
    for conflict in value.unresolved_conflicts:
        _text(conflict)
    validate_relationship_assertion(value.assertion)
    _citations(value.citations)


def _citations(values: tuple[ClaimCitation, ...]) -> None:
    if not isinstance(values, tuple) or len(values) > 20:
        raise ValueError("Relationship citations must be bounded and immutable")
    if values:
        _validate_frozen_citations(values)


def revise_relationship_review(
    *,
    version: ReportVersion,
    revision_id: UUID,
    relationship_id: UUID,
    previous: RelationshipReviewRevision | None,
    evidence_label: str,
    disposition: RelationshipDisposition,
    rationale: str,
    unresolved_conflicts: tuple[str, ...],
    citations: tuple[ClaimCitationInput, ...],
    actor_id: UUID,
    now: datetime,
) -> RelationshipReviewRevision:
    assertion = freeze_relationship_assertion(version, evidence_label)
    if not isinstance(citations, tuple) or len(citations) > 20:
        raise ValueError("Relationship citations must be bounded")
    frozen = freeze_claim_citations(version, citations) if citations else ()
    if previous is not None:
        validate_relationship_revision(previous)
        if (
            previous.relationship_id != relationship_id
            or previous.report_id != version.report_id
            or previous.report_version_id != version.id
            or previous.assertion != assertion
            or previous.id == revision_id
            or previous.created_at > now
        ):
            raise ValueError("Relationship corrections must preserve their original anchors")
    value = RelationshipReviewRevision(
        revision_id,
        relationship_id,
        version.report_id,
        version.id,
        previous.number + 1 if previous else 1,
        previous.id if previous else None,
        assertion,
        disposition,
        rationale,
        unresolved_conflicts,
        frozen,
        actor_id,
        now,
    )
    validate_relationship_revision(value)
    return value

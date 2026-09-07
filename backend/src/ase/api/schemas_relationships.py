"""Operator relationship edits cannot supply subject, scope, author or source snapshots."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_claims import CitationInput
from ase.application.reports.relationships import RelationshipReviewInput
from ase.domain.claim_revisions import ClaimCitationInput
from ase.domain.relationship_assertions import RelationshipAssertionSnapshot
from ase.domain.relationship_review import RelationshipDisposition, RelationshipReviewRevision
from ase.domain.relationship_roots import RelationshipReviewRoot


class RelationshipAssertionsOut(BaseModel):
    items: list[RelationshipAssertionSnapshot]
    unavailable_labels: list[str]
    review_ids: dict[str, UUID]


class RelationshipEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_label: str = Field(min_length=1, max_length=64)
    disposition: RelationshipDisposition
    rationale: str = Field(min_length=1, max_length=1200)
    unresolved_conflicts: list[Annotated[str, Field(min_length=1, max_length=1200)]] = Field(
        default_factory=list, max_length=20
    )
    citations: list[CitationInput] = Field(default_factory=list, max_length=20)

    def to_domain(self) -> RelationshipReviewInput:
        return RelationshipReviewInput(
            self.evidence_label,
            self.disposition,
            self.rationale,
            tuple(self.unresolved_conflicts),
            tuple(
                ClaimCitationInput(row.label, row.relation, row.field, row.start, row.end, row.text)
                for row in self.citations
            ),
        )


class RelationshipCreateIn(RelationshipEditIn):
    report_id: UUID
    version_number: int = Field(strict=True, ge=1, le=2_147_483_647)


class RelationshipUpdateIn(RelationshipEditIn):
    base_revision_id: UUID


class RelationshipDetailOut(BaseModel):
    root: RelationshipReviewRoot
    revision: RelationshipReviewRevision


class RelationshipPageOut(BaseModel):
    items: list[RelationshipReviewRevision]
    total: int
    offset: int
    limit: int

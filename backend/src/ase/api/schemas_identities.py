"""Operator identity edits cannot supply subject, scope, author or source snapshots."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_claims import CitationInput
from ase.application.reports.identities import IdentityReviewInput
from ase.domain.claim_revisions import ClaimCitationInput
from ase.domain.identity_review import IdentityDecisionRevision, IdentityDisposition
from ase.domain.identity_roots import IdentityDecisionRoot


class IdentityEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_label: str = Field(min_length=1, max_length=64)
    disposition: IdentityDisposition
    rationale: str = Field(min_length=1, max_length=1200)
    unresolved_conflicts: list[Annotated[str, Field(min_length=1, max_length=1200)]] = Field(
        default_factory=list, max_length=20
    )
    citations: list[CitationInput] = Field(default_factory=list, max_length=20)

    def to_domain(self) -> IdentityReviewInput:
        return IdentityReviewInput(
            self.candidate_label,
            self.disposition,
            self.rationale,
            tuple(self.unresolved_conflicts),
            tuple(
                ClaimCitationInput(row.label, row.relation, row.field, row.start, row.end, row.text)
                for row in self.citations
            ),
        )


class IdentityCreateIn(IdentityEditIn):
    report_id: UUID
    version_number: int = Field(strict=True, ge=1, le=2_147_483_647)


class IdentityUpdateIn(IdentityEditIn):
    base_revision_id: UUID


class IdentityDetailOut(BaseModel):
    root: IdentityDecisionRoot
    revision: IdentityDecisionRevision


class IdentityPageOut(BaseModel):
    items: list[IdentityDecisionRevision]
    total: int
    offset: int
    limit: int

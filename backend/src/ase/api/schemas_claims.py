"""Bounded operator claim edits; audit identities and timestamps are server-owned."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.application.reports.claims import ClaimInput
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    ClaimReviewState,
    ClaimRevision,
)
from ase.domain.claim_roots import ClaimRoot


class CitationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=32)
    relation: ClaimRelation
    field: Literal["title", "summary"]
    start: int = Field(strict=True, ge=0, le=20000)
    end: int = Field(strict=True, ge=1, le=20000)
    text: str = Field(min_length=1, max_length=1200)


class ClaimEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=1200)
    kind: ClaimKind
    state: ClaimReviewState = ClaimReviewState.PROPOSED
    citations: list[CitationInput] = Field(min_length=1, max_length=20)
    unresolved_conflicts: list[Annotated[str, Field(min_length=1, max_length=1200)]] = Field(
        default_factory=list, max_length=20
    )
    reason: str = Field(min_length=1, max_length=1200)

    def to_domain(self) -> ClaimInput:
        return ClaimInput(
            self.statement,
            self.kind,
            self.state,
            tuple(
                ClaimCitationInput(row.label, row.relation, row.field, row.start, row.end, row.text)
                for row in self.citations
            ),
            tuple(self.unresolved_conflicts),
            self.reason,
        )


class ClaimGenerateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_id: UUID
    version_number: int = Field(strict=True, ge=1, le=2_147_483_647)


class ClaimCreateIn(ClaimEditIn):
    report_id: UUID
    version_number: int = Field(strict=True, ge=1, le=2_147_483_647)


class ClaimUpdateIn(ClaimEditIn):
    base_revision_id: UUID


class ClaimDetailOut(BaseModel):
    root: ClaimRoot
    revision: ClaimRevision


class ClaimPageOut(BaseModel):
    items: list[ClaimRevision]
    total: int
    offset: int
    limit: int

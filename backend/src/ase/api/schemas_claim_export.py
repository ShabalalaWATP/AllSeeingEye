"""Explicit bounded selection for an immutable report-version evidence package."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
)


class ClaimExportReferenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: UUID
    revision_id: UUID


class IdentityExportReferenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_id: UUID
    revision_id: UUID


class ClaimPackageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_number: int = Field(strict=True, ge=1, le=2_147_483_647)
    revisions: list[ClaimExportReferenceIn] = Field(default_factory=list, max_length=20)
    identity_revisions: list[IdentityExportReferenceIn] = Field(default_factory=list, max_length=20)

    asset_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def selection_bounds(self) -> Self:
        if not 1 <= len(self.revisions) + len(self.identity_revisions) + len(self.asset_ids) <= 20:
            raise ValueError("Select between one and twenty annotations or original assets.")
        if len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError("Each original asset must be selected once.")
        return self

    def references(self) -> tuple[ClaimExportReference, ...]:
        return tuple(ClaimExportReference(row.claim_id, row.revision_id) for row in self.revisions)

    def identity_references(self) -> tuple[IdentityExportReference, ...]:
        return tuple(
            IdentityExportReference(row.decision_id, row.revision_id)
            for row in self.identity_revisions
        )

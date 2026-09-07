"""Bounded explicit selections and declared correspondence, never client-provided evidence."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from ase.api.schemas_claim_export import (
    ClaimExportReferenceIn,
    IdentityExportReferenceIn,
    RelationshipExportReferenceIn,
)
from ase.api.schemas_reports import ReportSummaryOut
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
    RelationshipExportReference,
)
from ase.application.reports.comparison_inputs import ComparisonInput, ComparisonSelection
from ase.domain.annotation_comparison import (
    AnnotationComparison,
    AnnotationCorrespondence,
    AnnotationKind,
    JudgementCorrespondence,
)


class ComparisonSelectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_id: UUID
    version_number: int = Field(strict=True, ge=1, le=2_147_483_647)
    revisions: list[ClaimExportReferenceIn] = Field(default_factory=list, max_length=20)
    identity_revisions: list[IdentityExportReferenceIn] = Field(default_factory=list, max_length=20)
    relationship_revisions: list[RelationshipExportReferenceIn] = Field(
        default_factory=list, max_length=20
    )

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if (
            len(self.revisions) + len(self.identity_revisions) + len(self.relationship_revisions)
            > 20
        ):
            raise ValueError("Select at most twenty annotation revisions per side")
        return self

    def to_domain(self) -> ComparisonSelection:
        return ComparisonSelection(
            self.report_id,
            self.version_number,
            tuple(ClaimExportReference(row.claim_id, row.revision_id) for row in self.revisions),
            tuple(
                IdentityExportReference(row.decision_id, row.revision_id)
                for row in self.identity_revisions
            ),
            tuple(
                RelationshipExportReference(row.relationship_id, row.revision_id)
                for row in self.relationship_revisions
            ),
        )


class AnnotationCorrespondenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: AnnotationKind
    before_revision_id: UUID
    after_revision_id: UUID
    rationale: str = Field(min_length=1, max_length=500)


class JudgementCorrespondenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before_judgement_id: str = Field(min_length=1, max_length=16)
    after_judgement_id: str = Field(min_length=1, max_length=16)
    rationale: str = Field(min_length=1, max_length=500)


class AnnotationComparisonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before: ComparisonSelectionIn
    after: ComparisonSelectionIn
    correspondences: list[AnnotationCorrespondenceIn] = Field(default_factory=list, max_length=20)
    judgement_correspondences: list[JudgementCorrespondenceIn] = Field(
        default_factory=list, max_length=20
    )

    def to_domain(self) -> ComparisonInput:
        return ComparisonInput(
            self.before.to_domain(),
            self.after.to_domain(),
            tuple(AnnotationCorrespondence(**row.model_dump()) for row in self.correspondences),
            tuple(
                JudgementCorrespondence(**row.model_dump())
                for row in self.judgement_correspondences
            ),
        )


class AnnotationComparisonExportIn(AnnotationComparisonIn):
    expected_comparison_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AnnotationComparisonOut(RootModel[AnnotationComparison]):
    pass


class ComparisonReportsOut(BaseModel):
    items: list[ReportSummaryOut]
    total: int
    offset: int
    limit: int

"""Team copy disclosure preview, request, result and provenance."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ase.application.reports.team_copies import (
    MAX_DISCLOSED_LABELS,
    TeamCopyPreview,
    TeamCopyProvenance,
    TeamCopyResult,
)
from ase.domain.report_team_copy import TeamCopyOmission

EvidenceLabel = Annotated[str, StringConstraints(pattern=r"^E[1-9][0-9]{0,3}$")]


class PrivateInputOut(BaseModel):
    label: str
    title: str
    source_id: str


class LinkedArtefactsOut(BaseModel):
    """Records attached to the personal version that stay with it and are not copied."""

    claims: int
    original_files: int
    original_passages: int
    reviewed_snapshots: int
    map_views: int


class TeamCopyPreviewOut(BaseModel):
    team_id: UUID
    team_name: str
    source_version_number: int
    private_inputs: list[PrivateInputOut]
    omissions: list[TeamCopyOmission]
    omitted_scope_keys: list[str]
    not_copied: LinkedArtefactsOut
    content_sha256: str
    existing_report_id: UUID | None

    @classmethod
    def build(cls, preview: TeamCopyPreview) -> Self:
        plan, linked = preview.plan, preview.linked
        return cls(
            team_id=preview.team.id,
            team_name=preview.team.name,
            source_version_number=preview.source_version_number,
            private_inputs=[
                PrivateInputOut(label=row.label, title=row.title, source_id=row.source_id)
                for row in plan.private_inputs
            ],
            omissions=list(plan.omissions),
            omitted_scope_keys=list(plan.omitted_scope_keys),
            not_copied=LinkedArtefactsOut(
                claims=linked.claims,
                original_files=linked.original_files,
                original_passages=linked.original_passages,
                reviewed_snapshots=linked.reviewed_snapshots,
                map_views=linked.map_views,
            ),
            content_sha256=plan.content_sha256,
            existing_report_id=preview.existing.report_id if preview.existing else None,
        )


class TeamCopyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: UUID
    disclosed_evidence_labels: list[EvidenceLabel] = Field(
        default_factory=list, max_length=MAX_DISCLOSED_LABELS
    )


class TeamCopyOut(BaseModel):
    report_id: UUID
    version_number: int
    team_id: UUID
    copied_at: datetime
    created: bool

    @classmethod
    def build(cls, result: TeamCopyResult) -> Self:
        return cls(
            report_id=result.copy.report_id,
            version_number=1,
            team_id=result.copy.team_id,
            copied_at=result.copy.copied_at,
            created=result.created,
        )


class TeamCopyProvenanceOut(BaseModel):
    report_id: UUID
    team_id: UUID
    copied_by: UUID
    copied_by_name: str | None
    copied_at: datetime
    source_version_number: int
    source_report_id: UUID | None
    content_sha256: str
    disclosed_private_inputs: int
    omissions: list[TeamCopyOmission]

    @classmethod
    def build(cls, provenance: TeamCopyProvenance) -> Self:
        copy = provenance.copy
        return cls(
            report_id=copy.report_id,
            team_id=copy.team_id,
            copied_by=copy.copied_by,
            copied_by_name=provenance.copied_by_name,
            copied_at=copy.copied_at,
            source_version_number=copy.source_version_number,
            source_report_id=copy.source_report_id if provenance.source_visible else None,
            content_sha256=copy.content_sha256,
            disclosed_private_inputs=len(copy.disclosed_labels),
            omissions=list(copy.omissions),
        )

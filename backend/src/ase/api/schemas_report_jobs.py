"""Public progress and partial-section views for durable report jobs."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_reports import ReportCreateIn


class ReportJobCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    report: ReportCreateIn


class BriefJobCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    brief_id: UUID
    revision: int = Field(ge=1, strict=True)


class ReportJobUsageOut(BaseModel):
    calls: int
    max_calls: int
    output_tokens: int
    output_allowance: int
    uncertain_calls: int


class ReportJobSectionOut(BaseModel):
    id: str
    title: str
    kind: Literal["topic", "synthesis"]
    status: Literal["running", "completed", "split", "incomplete"]
    reporting: list[str] = Field(default_factory=list)
    assessment: str | None = None
    gaps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    error: str | None = None


class ReportJobOut(BaseModel):
    id: UUID
    brief_id: UUID | None = None
    brief_revision: int | None = None
    revision: int
    title: str
    status: Literal["queued", "running", "paused", "completed", "needs_review", "failed"]
    stage: str
    created_at: datetime
    updated_at: datetime
    team_id: UUID | None
    report_id: UUID | None
    model: str
    reasoning_effort: str | None
    error: str | None
    can_resume: bool
    completed_sections: int
    total_sections: int
    sections: list[ReportJobSectionOut]
    usage: ReportJobUsageOut


class ReportJobsOut(BaseModel):
    items: list[ReportJobOut]


def public_job(value: dict[str, Any]) -> ReportJobOut:
    return ReportJobOut.model_validate(value)

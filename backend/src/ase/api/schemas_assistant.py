"""Compact transient chat contract, separate from persisted reports."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.assistant import (
    AssistantAnswer,
    AssistantQuestion,
    AssistantReportSelection,
    AssistantSelection,
    AssistantTimeRange,
)
from ase.domain.events import BoundingBox, Category

AssistantSourceCategory = Category | Literal["camera", "infrastructure", "doctrine"]


class AssistantBoundsIn(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)


class AssistantSelectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["event", "camera", "infrastructure"]
    id: str = Field(min_length=1, max_length=160)


class AssistantTimeRangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    since: datetime
    until: datetime


class AssistantReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    version: int = Field(ge=1, le=1_000_000)


class AssistantAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    prior_questions: list[str] = Field(default_factory=list, max_length=4)
    scope: Literal["global", "viewport", "selected", "report"] = "global"
    bbox: AssistantBoundsIn | None = None
    selected: AssistantSelectionIn | None = None
    time_range: AssistantTimeRangeIn | None = None
    continuation_id: str | None = Field(default=None, min_length=16, max_length=80)
    source_categories: list[AssistantSourceCategory] | None = Field(
        default=None, min_length=1, max_length=14
    )
    report: AssistantReportIn | None = None

    def to_question(self) -> AssistantQuestion:
        return AssistantQuestion(
            self.question,
            tuple(self.prior_questions),
            self.scope,
            BoundingBox(**self.bbox.model_dump()) if self.bbox else None,
            AssistantSelection(**self.selected.model_dump()) if self.selected else None,
            AssistantTimeRange(**self.time_range.model_dump()) if self.time_range else None,
            self.continuation_id,
            tuple(str(value) for value in self.source_categories)
            if self.source_categories
            else None,
            AssistantReportSelection(**self.report.model_dump()) if self.report else None,
        )

    @model_validator(mode="after")
    def valid_scope(self) -> Self:
        self.to_question()
        return self


class AssistantPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    lon: float
    lat: float


class AssistantSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: Literal[
        "event", "camera", "infrastructure", "gnss", "doctrine", "report_claim", "report_evidence"
    ]
    record_id: str
    source_id: str
    title: str
    url: str | None
    published_at: datetime | None
    observed_at: datetime | None
    point: AssistantPointOut | None
    grade: str | None


class AssistantParagraphOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: Literal["finding", "inference", "gap"]
    text: str
    citations: list[str]


class AssistantScopeOut(BaseModel):
    mode: Literal["global", "viewport", "selected", "report"]
    bbox: AssistantBoundsIn | None
    selected: AssistantSelectionIn | None


class AssistantCoverageOut(BaseModel):
    candidate_count: int
    matched_count: int
    selected_count: int
    source_count: int
    capped: bool
    notes: list[str]


class AssistantInterpretationOut(BaseModel):
    topics: list[str]
    countries: list[str]
    since: datetime | None
    until: datetime | None
    time_basis: Literal["publication"]
    notes: list[str]
    source_categories: list[str]


class AssistantModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    reasoning_effort: str | None


class AssistantReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version_id: UUID
    version: int
    title: str
    data_cutoff: datetime | None


class AssistantAnswerOut(BaseModel):
    paragraphs: list[AssistantParagraphOut]
    sources: list[AssistantSourceOut]
    scope: AssistantScopeOut
    coverage: AssistantCoverageOut
    interpretation: AssistantInterpretationOut
    continuation_id: str | None
    generated_at: datetime
    model: AssistantModelOut | None
    report: AssistantReportOut | None = None

    @classmethod
    def from_answer(cls, answer: AssistantAnswer) -> Self:
        question, context = answer.question, answer.context
        return cls(
            paragraphs=[AssistantParagraphOut.model_validate(row) for row in answer.paragraphs],
            sources=[AssistantSourceOut.model_validate(row) for row in context.sources],
            scope=AssistantScopeOut(
                mode=question.scope,
                bbox=AssistantBoundsIn(
                    west=question.bbox.west,
                    south=question.bbox.south,
                    east=question.bbox.east,
                    north=question.bbox.north,
                )
                if question.bbox
                else None,
                selected=AssistantSelectionIn(kind=question.selected.kind, id=question.selected.id)
                if question.selected
                else None,
            ),
            coverage=AssistantCoverageOut(
                candidate_count=context.candidate_count,
                matched_count=context.matched_count,
                selected_count=len(context.sources),
                source_count=context.source_count,
                capped=context.capped,
                notes=list(context.notes),
            ),
            interpretation=AssistantInterpretationOut(
                topics=list(context.interpretation.topics) if context.interpretation else [],
                countries=list(context.interpretation.countries) if context.interpretation else [],
                since=context.interpretation.since if context.interpretation else None,
                until=context.interpretation.until if context.interpretation else None,
                time_basis="publication",
                notes=list(context.interpretation.notes) if context.interpretation else [],
                source_categories=list(context.interpretation.source_categories)
                if context.interpretation
                else [],
            ),
            continuation_id=answer.continuation_id,
            generated_at=answer.generated_at,
            model=AssistantModelOut.model_validate(answer.model) if answer.model else None,
            report=AssistantReportOut.model_validate(context.report) if context.report else None,
        )

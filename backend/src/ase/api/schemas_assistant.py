"""Compact transient chat contract, separate from persisted reports."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.assistant import AssistantAnswer, AssistantQuestion, AssistantSelection
from ase.domain.events import BoundingBox


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


class AssistantAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    prior_questions: list[str] = Field(default_factory=list, max_length=4)
    scope: Literal["global", "viewport", "selected"] = "global"
    bbox: AssistantBoundsIn | None = None
    selected: AssistantSelectionIn | None = None

    def to_question(self) -> AssistantQuestion:
        return AssistantQuestion(
            self.question,
            tuple(self.prior_questions),
            self.scope,
            BoundingBox(**self.bbox.model_dump()) if self.bbox else None,
            AssistantSelection(**self.selected.model_dump()) if self.selected else None,
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
    kind: Literal["event", "camera", "infrastructure", "gnss"]
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
    mode: Literal["global", "viewport", "selected"]
    bbox: AssistantBoundsIn | None
    selected: AssistantSelectionIn | None


class AssistantCoverageOut(BaseModel):
    candidate_count: int
    matched_count: int
    selected_count: int
    source_count: int
    capped: bool
    notes: list[str]


class AssistantModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    reasoning_effort: str | None


class AssistantAnswerOut(BaseModel):
    paragraphs: list[AssistantParagraphOut]
    sources: list[AssistantSourceOut]
    scope: AssistantScopeOut
    coverage: AssistantCoverageOut
    generated_at: datetime
    model: AssistantModelOut | None

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
            generated_at=answer.generated_at,
            model=AssistantModelOut.model_validate(answer.model) if answer.model else None,
        )

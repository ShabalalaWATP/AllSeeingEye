"""Reviewer input excludes assessor identity, timestamps and applied policy versions."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from ase.application.reports.source_reviews import SourceReviewInput
from ase.domain.events import Credibility, Reliability
from ase.domain.source_assessment import Authenticity
from ase.domain.source_reviews import SourceReviewKind

ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class SourceReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: ShortText
    judgement_id: ShortText
    subject: ShortText
    kind: SourceReviewKind
    basis: Annotated[str, Field(min_length=1, max_length=1000)]
    previous_id: UUID | None = None
    reliability: Reliability | None = None
    expertise_basis: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    credibility: Annotated[StrictInt, Field(ge=1, le=6)] | None = None
    authenticity: Authenticity | None = None
    policy_note: Annotated[str, Field(min_length=1, max_length=1000)] | None = None

    def to_domain(self) -> SourceReviewInput:
        return SourceReviewInput(
            self.label,
            self.judgement_id,
            self.subject,
            self.kind,
            self.basis,
            self.previous_id,
            self.reliability,
            self.expertise_basis,
            Credibility(self.credibility) if self.credibility is not None else None,
            self.authenticity,
            self.policy_note,
        )


class SourceSnapshotIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subjects: dict[ShortText, ShortText]

    @field_validator("subjects")
    @classmethod
    def bounded_subjects(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 64:
            raise ValueError("Choose at most 64 exact judgement subject scopes.")
        return value

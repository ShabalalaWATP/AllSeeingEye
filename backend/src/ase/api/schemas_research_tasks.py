"""Bounded, explicitly supplied hypotheses and public-source search tasks."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
Term = Annotated[str, Field(min_length=1, max_length=300)]


class ResearchCandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: Identifier
    label: str = Field(min_length=1, max_length=200)
    identifiers: list[Term] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def bounded(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> ResearchCandidate:
        return ResearchCandidate(self.id, self.label, tuple(self.identifiers))


class PlannedQueryTaskIn(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: Identifier
    source_id: str = Field(min_length=1, max_length=120)
    purpose: Literal["challenge", "disambiguation"]
    terms: list[Term] = Field(min_length=1, max_length=12)
    candidate_id: Identifier | None = None

    @model_validator(mode="after")
    def bounded(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> PlannedQueryTask:
        return PlannedQueryTask(
            self.id, self.source_id, self.purpose, tuple(self.terms), self.candidate_id
        )

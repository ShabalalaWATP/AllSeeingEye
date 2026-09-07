"""Editable deterministic plans use source IDs, never client-supplied fetch URLs."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.api.schemas_map_origin import MapResearchOriginOut
from ase.api.schemas_research_area import ResearchAreaOut
from ase.api.schemas_research_tasks import PlannedQueryTaskIn, ResearchCandidateIn
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_plan import UNKNOWN_SPATIAL_SCOPE, QueryVariant


class QueryVariantIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    language: str = Field(min_length=2, max_length=16)
    terms: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def bounded(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> QueryVariant:
        return QueryVariant(self.language, tuple(self.terms))


class ResearchPlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    since: datetime
    until: datetime
    languages: list[str] = Field(default_factory=lambda: ["en"], min_length=1, max_length=8)
    terms: list[str] = Field(default_factory=list, max_length=12)
    mode: ResearchMode = ResearchMode.QUICK
    focus: ResearchFocus = ResearchFocus.GENERAL
    subject: str | None = Field(default=None, max_length=300)
    country_iso: str | None = Field(default=None, min_length=2, max_length=2)
    source_ids: list[str] | None = Field(default=None, max_length=64)
    time_basis: EvidenceTimeBasis | None = None
    query_variants: list[QueryVariantIn] = Field(default_factory=list, max_length=8)
    candidate_hypotheses: list[ResearchCandidateIn] = Field(default_factory=list, max_length=8)
    planned_tasks: list[PlannedQueryTaskIn] = Field(default_factory=list, max_length=8)
    map_view_id: UUID | None = None
    map_revision_id: UUID | None = None
    team_id: UUID | None = None

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if (self.map_view_id is None) != (self.map_revision_id is None):
            raise ValueError("Choose both saved map and revision identifiers")
        self.to_query()
        return self

    def to_query(self) -> ResearchQuery:
        if sum(map(len, self.terms)) > 1000:
            raise ValueError("Provide at most 1000 combined search-term characters")
        return ResearchQuery(
            question=self.question,
            time_basis=self.time_basis,
            since=self.since,
            until=self.until,
            languages=tuple(self.languages),
            terms=tuple(self.terms),
            mode=self.mode,
            focus=self.focus,
            subject=self.subject,
            country_iso=self.country_iso.upper() if self.country_iso else None,
            source_ids=tuple(self.source_ids) if self.source_ids is not None else None,
            query_variants=tuple(variant.to_domain() for variant in self.query_variants),
            candidate_hypotheses=tuple(row.to_domain() for row in self.candidate_hypotheses),
            planned_tasks=tuple(row.to_domain() for row in self.planned_tasks),
        )


class ResearchTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: str
    source_name: str
    selected: bool
    supported: bool
    language: str | None
    terms: list[str]
    provenance: str
    temporal_scope: str
    query_language: str | None = None
    spatial_supported: bool = False
    spatial_scope: str = UNKNOWN_SPATIAL_SCOPE
    task_id: str | None = None
    purpose: Literal["baseline", "challenge", "disambiguation"] = "baseline"
    candidate_id: str | None = None
    planned_terms_supported: bool = False


class QueryTransformationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    original_terms: list[str]
    languages: list[str]
    model: str
    status: Literal["completed", "failed", "unavailable"]
    variants: list[QueryVariantIn]
    policy_version: str


class ResearchPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    question: str
    since: datetime
    until: datetime
    languages: list[str]
    tasks: list[ResearchTaskOut]
    request_limit: int
    seconds_limit: float
    item_limit: int
    policy_version: str
    model_calls: int
    translation_calls: int
    replans: int
    focus: str
    mode: str
    subject: str | None
    country_iso: str | None
    translation: QueryTransformationOut | None = None
    area: ResearchAreaOut | None = None
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION
    candidate_hypotheses: list[ResearchCandidateIn] = Field(default_factory=list, max_length=8)


class ResearchPreviewOut(ResearchPlanOut):
    map_origin: MapResearchOriginOut | None = None

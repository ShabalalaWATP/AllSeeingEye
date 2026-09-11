"""Editable deterministic plans use source IDs, never client-supplied fetch URLs."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from ase.api.schemas_map_origin import MapResearchOriginOut
from ase.api.schemas_research_area import ResearchAreaIn, ResearchAreaOut
from ase.api.schemas_research_tasks import (
    PlannedQueryTaskIn,
    PlannedQueryTaskOut,
    ResearchCandidateIn,
    ResearchCandidateOut,
)
from ase.application.reports.request import ReportRequest
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.registry_identifiers import RegistryLookup
from ase.domain.research import ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_plan import UNKNOWN_SPATIAL_SCOPE, QueryVariant
from ase.domain.research_scope import validate_research_interval


class QueryVariantIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    language: str = Field(min_length=2, max_length=16)
    terms: list[str] = Field(min_length=1, max_length=12)
    kind: Literal["translation", "transliteration"] = "translation"
    original_terms: list[str] = Field(default_factory=list, max_length=12)
    source_script: str | None = Field(default=None, pattern=r"^[A-Z][a-z]{3}$")
    target_script: str | None = Field(default=None, pattern=r"^[A-Z][a-z]{3}$")
    method: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def bounded(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> QueryVariant:
        return QueryVariant(
            self.language,
            tuple(self.terms),
            self.kind,
            tuple(self.original_terms),
            self.source_script,
            self.target_script,
            self.method,
        )


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
    countries: list[Annotated[str, Field(min_length=2, max_length=2)]] = Field(
        default_factory=list, max_length=8
    )
    research_web_search: StrictBool = False
    source_ids: list[str] | None = Field(default=None, max_length=64)
    time_basis: EvidenceTimeBasis | None = None
    query_variants: list[QueryVariantIn] = Field(default_factory=list, max_length=8)
    candidate_hypotheses: list[ResearchCandidateIn] = Field(default_factory=list, max_length=8)
    planned_tasks: list[PlannedQueryTaskIn] = Field(default_factory=list, max_length=8)
    map_view_id: UUID | None = None
    map_revision_id: UUID | None = None
    team_id: UUID | None = None
    research_area: ResearchAreaIn | None = None

    @model_validator(mode="after")
    def bounded(self) -> Self:
        validate_research_interval(
            self.since,
            self.until,
            recorded=self.time_basis is EvidenceTimeBasis.RECORDED,
            now=datetime.now(UTC),
        )
        if (self.country_iso or self.countries) and self.focus is not ResearchFocus.GENERAL:
            raise ValueError("Country filters are unavailable for record-focused research")
        if self.research_web_search and self.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}:
            raise ValueError("Fresh web search requires public-source research")
        if (self.map_view_id is None) != (self.map_revision_id is None):
            raise ValueError("Choose both saved map and revision identifiers")
        if self.research_area is not None:
            ReportRequest(
                "ask",
                question=self.question,
                research_mode=self.mode,
                research_focus=self.focus,
                country_iso=self.country_iso,
                country_isos=tuple(self.countries),
                research_web_search=self.research_web_search,
                research_area=self.research_area.to_domain(),
                map_view_id=self.map_view_id,
                map_revision_id=self.map_revision_id,
                research_since=self.since,
                research_until=self.until,
                research_time_basis=self.time_basis,
            )
        self.to_query()
        return self

    def to_query(self) -> ResearchQuery:
        if sum(map(len, self.terms)) > 1000:
            raise ValueError("Provide at most 1000 combined search-term characters")
        for variant in self.query_variants:
            if variant.original_terms and variant.original_terms != self.terms:
                raise ValueError("Transliteration must reference the exact original query terms")
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
            country_isos=tuple(self.countries),
            research_web_search=self.research_web_search,
            source_ids=tuple(self.source_ids) if self.source_ids is not None else None,
            query_variants=tuple(variant.to_domain() for variant in self.query_variants),
            candidate_hypotheses=tuple(row.to_domain() for row in self.candidate_hypotheses),
            planned_tasks=tuple(row.to_domain() for row in self.planned_tasks),
            area=self.research_area.to_domain() if self.research_area else None,
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
    query_variant: QueryVariantIn | None = None
    spatial_supported: bool = False
    spatial_scope: str = UNKNOWN_SPATIAL_SCOPE
    task_id: str | None = None
    purpose: Literal["baseline", "challenge", "disambiguation"] = "baseline"
    candidate_id: str | None = None
    planned_terms_supported: bool = False
    registry_lookup: RegistryLookup | None = None
    registry_namespaces: list[str] = Field(default_factory=list)
    registry_options: list[RegistryLookup] = Field(default_factory=list)


class QueryTransformationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    original_terms: list[str]
    languages: list[str]
    model: str
    status: Literal["completed", "failed", "unavailable"]
    variants: list[QueryVariantIn]
    policy_version: str


class EvidenceExcerptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: str
    source_id: str
    content_hash: str
    field: Literal["title", "summary"]
    quote: str


class ContinuationTraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    decision: Literal["continue", "replan", "sufficient"]
    requested_decision: Literal["continue", "replan", "sufficient"] | None = None
    basis: Literal[
        "empty_results",
        "potential_conflict",
        "question_addressed",
        "insufficient_context",
        "invalid_or_unavailable",
    ]
    rationale: str
    citations: list[EvidenceExcerptOut]
    gaps: list[str]
    model: str
    context_count: int
    total_count: int
    override_reason: str | None = None
    policy_version: Literal["ase-collection-review-v1"] = "ase-collection-review-v1"


class PlanningTraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: Literal["applied", "empty", "rejected", "unavailable", "skipped"]
    requested_model: str = Field(max_length=2048)
    returned_model: str = Field(max_length=2048)
    call_count: int = Field(ge=0, le=1)
    reason: str = Field(max_length=500)
    proposed_candidates: list[ResearchCandidateOut] = Field(max_length=8)
    proposed_tasks: list[PlannedQueryTaskOut] = Field(max_length=8)
    accepted_candidate_ids: list[str] = Field(max_length=8)
    accepted_task_ids: list[str] = Field(max_length=8)
    policy_version: Literal["ase-model-plan-v1"]


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
    country_isos: list[str] = Field(default_factory=list, max_length=8)
    research_web_search: bool = False
    translation: QueryTransformationOut | None = None
    area: ResearchAreaOut | None = None
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION
    candidate_hypotheses: list[ResearchCandidateOut] = Field(default_factory=list, max_length=8)

    continuation: ContinuationTraceOut | None = None
    planning: PlanningTraceOut | None = None


class ResearchPreviewOut(ResearchPlanOut):
    map_origin: MapResearchOriginOut | None = None

"""Request and response models for reports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, StrictBool, model_validator

from ase.api.schemas_challenge import ReportChallengeOut
from ase.api.schemas_citation_checks import ReportCitationChecksOut
from ase.api.schemas_claim_ledger import ClaimLedgerOut
from ase.api.schemas_model_routing import ModelRoutingOut
from ase.api.schemas_report_assessment import ReportAssessmentOut
from ase.api.schemas_report_documents import ReportPublicationOut
from ase.api.schemas_report_evidence import ReportEvidenceOut
from ase.api.schemas_research import ResearchReceiptOut
from ase.api.schemas_research_area import ResearchAreaIn
from ase.api.schemas_research_context import ResearchContextOut
from ase.api.schemas_research_plan import QueryVariantIn
from ase.api.schemas_research_tasks import PlannedQueryTaskIn, ResearchCandidateIn
from ase.application.reports.document import build_document
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import (
    AREA_DEFAULT_TEMPLATE,
    TEMPLATES,
    Template,
)
from ase.domain.advocacy import advocacy_to_dict
from ase.domain.claim_generation import ClaimGenerationReceipt
from ase.domain.claim_ledger import build_claim_ledger
from ase.domain.direction import direction_to_dict
from ase.domain.events import Category
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.languages import LANGUAGE_CODE_PATTERN, ReportLanguage
from ase.domain.report_records import (
    ReportRecord,
    ReportVersion,
    body_to_dict,
    findings_to_list,
    quality_to_dict,
)
from ase.domain.reports import ReportStatus
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_scope import MAX_RESEARCH_HOURS, validate_research_interval
from ase.domain.source_review_records import SourceReviewSnapshot


class ReportCreateIn(BaseModel):
    template: str = Field(min_length=1, max_length=32)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    countries: list[Annotated[str, Field(min_length=2, max_length=2)]] = Field(
        default_factory=list, max_length=8
    )
    categories: list[Category] = Field(default_factory=list, max_length=11)
    question: str | None = Field(default=None, max_length=1000)
    window_hours: int | None = Field(default=None, ge=1, le=MAX_RESEARCH_HOURS)
    profile_id: UUID | None = None
    devils_advocacy: bool = False
    hazard: str | None = Field(default=None, max_length=32)
    conflict: str | None = Field(default=None, max_length=64)
    plan: UUID | None = None
    team_id: UUID | None = None
    report_language: ReportLanguage = "en"
    report_style: Literal["briefing", "assessment"] = "assessment"
    research_mode: ResearchMode | None = None
    research_web_search: StrictBool = False
    research_languages: list[Annotated[str, Field(pattern=LANGUAGE_CODE_PATTERN)]] = Field(
        default_factory=lambda: ["en"], min_length=1, max_length=8
    )
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_source_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] | None = Field(
        default=None, max_length=64
    )
    research_query_variants: list[QueryVariantIn] = Field(default_factory=list, max_length=8)
    research_candidate_hypotheses: list[ResearchCandidateIn] = Field(
        default_factory=list, max_length=8
    )
    research_planned_tasks: list[PlannedQueryTaskIn] = Field(default_factory=list, max_length=8)
    research_terms: list[Annotated[str, Field(min_length=1, max_length=300)]] | None = Field(
        default=None, max_length=12
    )
    research_subject: str | None = Field(default=None, max_length=300)
    research_input_id: UUID | None = None
    parent_report_id: UUID | None = None
    parent_version: int | None = Field(default=None, ge=1)
    map_view_id: UUID | None = None
    map_revision_id: UUID | None = None
    disclose_area_to_provider: StrictBool = False
    research_area: ResearchAreaIn | None = None
    research_since: AwareDatetime | None = None
    research_until: AwareDatetime | None = None
    research_time_basis: EvidenceTimeBasis | None = None

    @model_validator(mode="after")
    def research_requires_question(self) -> Self:
        if self.research_since is not None and self.research_until is not None:
            validate_research_interval(
                self.research_since,
                self.research_until,
                recorded=self.research_time_basis is EvidenceTimeBasis.RECORDED,
                now=datetime.now(UTC),
            )
        if self.research_terms is not None and (
            any(not term.strip() for term in self.research_terms)
            or sum(map(len, self.research_terms)) > 1000
        ):
            raise ValueError("Provide bounded explicit research terms")
        variants = [row.language.lower() for row in self.research_query_variants]
        if len(set(variants)) != len(variants) or not set(variants).issubset(
            language.lower() for language in self.research_languages
        ):
            raise ValueError("Query variants must uniquely match selected research languages")
        if self.research_source_ids is not None and len(set(self.research_source_ids)) != len(
            self.research_source_ids
        ):
            raise ValueError("Selected research sources must be unique")
        if self.research_mode and (not self.question or not self.question.strip()):
            raise ValueError("On-demand research requires a question")
        if self.research_mode and self.country and self.research_focus is not ResearchFocus.GENERAL:
            raise ValueError("Country filters are unavailable for record-focused research")
        if (self.map_view_id is None) != (self.map_revision_id is None):
            raise ValueError("Choose both saved map and revision identifiers")
        self.to_request()
        return self

    def _template_id(self) -> str:
        """A new drawn-area or map-object request gets the area product, not free text.

        Regeneration rebuilds a saved report from its stored scope and template, so an
        existing area report keeps the product it was written as.
        """
        chosen = self.template.strip().lower()
        area = self.research_area is not None or self.map_view_id is not None
        return AREA_DEFAULT_TEMPLATE if area and chosen == "ask" else chosen

    def to_request(self) -> ReportRequest:
        return ReportRequest(
            template_id=self._template_id(),
            country_iso=self.country.upper() if self.country else None,
            country_isos=tuple(self.countries),
            research_web_search=self.research_web_search,
            categories=tuple(self.categories),
            question=self.question.strip() if self.question else None,
            window_hours=self.window_hours,
            profile_id=self.profile_id,
            devils_advocacy=self.devils_advocacy,
            hazard=self.hazard.strip().lower() if self.hazard else None,
            conflict_id=self.conflict.strip().lower() if self.conflict else None,
            plan_id=self.plan,
            team_id=self.team_id,
            report_language=self.report_language,
            report_style=self.report_style,
            research_mode=self.research_mode,
            research_languages=tuple(dict.fromkeys(self.research_languages)),
            research_focus=self.research_focus,
            research_source_ids=tuple(self.research_source_ids)
            if self.research_source_ids is not None
            else None,
            research_query_variants=tuple(row.to_domain() for row in self.research_query_variants),
            research_candidate_hypotheses=tuple(
                row.to_domain() for row in self.research_candidate_hypotheses
            ),
            research_planned_tasks=tuple(row.to_domain() for row in self.research_planned_tasks),
            research_terms=tuple(self.research_terms) if self.research_terms is not None else None,
            research_subject=self.research_subject,
            research_input_id=self.research_input_id,
            parent_report_id=self.parent_report_id,
            parent_version=self.parent_version,
            map_view_id=self.map_view_id,
            map_revision_id=self.map_revision_id,
            disclose_area_to_provider=self.disclose_area_to_provider,
            research_area=self.research_area.to_domain() if self.research_area else None,
            research_since=self.research_since,
            research_time_basis=self.research_time_basis,
            research_until=self.research_until,
        )


class TemplateOut(BaseModel):
    id: str
    title: str
    purpose: str
    needs_country: bool
    needs_question: bool
    needs_conflict: bool
    needs_hazard: bool
    window_hours: int

    @classmethod
    def from_template(cls, template: Template) -> Self:
        return cls(
            id=template.id,
            title=template.title,
            purpose=template.purpose,
            needs_country=template.needs_country,
            needs_question=template.needs_question,
            needs_conflict=template.needs_conflict,
            needs_hazard=template.needs_hazard,
            window_hours=template.strategy.window_hours,
        )


class TemplatesOut(BaseModel):
    items: list[TemplateOut]

    @classmethod
    def all(cls) -> Self:
        return cls(items=[TemplateOut.from_template(t) for t in TEMPLATES.values()])


class ReportSummaryOut(BaseModel):
    id: UUID
    template: str
    title: str
    scope: dict[str, Any]
    period_from: datetime
    period_to: datetime
    status: ReportStatus
    created_by: UUID
    created_at: datetime
    latest_version: int
    team_id: UUID | None

    @classmethod
    def from_record(cls, record: ReportRecord) -> Self:
        return cls(
            id=record.id,
            template=record.template,
            title=record.title,
            scope=dict(record.scope),
            period_from=record.period_from,
            period_to=record.period_to,
            status=record.status,
            created_by=record.created_by,
            created_at=record.created_at,
            latest_version=record.latest_version,
            team_id=record.team_id,
        )


class ReportsOut(BaseModel):
    items: list[ReportSummaryOut]


class ReportVersionOut(BaseModel):
    brief_id: UUID | None = None
    brief_revision: int | None = None
    canonical_requirements: list[IntelligenceRequirement] = Field(default_factory=list)
    publication: ReportPublicationOut | None = None
    reviewed_source_snapshot: SourceReviewSnapshot | None = None
    claim_generation: ClaimGenerationReceipt | None = None
    claim_ledger: ClaimLedgerOut | None = None
    model_routing: ModelRoutingOut | None = None
    research_context: ResearchContextOut | None = None
    challenge: ReportChallengeOut | None = None
    citation_checks: ReportCitationChecksOut | None = None
    research: ResearchReceiptOut | None = None
    assessment: ReportAssessmentOut | None = None
    period_from: datetime | None
    period_to: datetime | None
    data_cutoff: datetime | None
    number: int
    status: ReportStatus
    body: dict[str, Any]
    findings: list[dict[str, str]]
    evidence: list[ReportEvidenceOut]
    quality: dict[str, Any]
    markdown: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float
    attempts: int
    created_at: datetime
    direction: dict[str, Any] | None
    devils_advocacy: dict[str, Any] | None

    @classmethod
    def from_version(
        cls,
        version: ReportVersion,
        record: ReportRecord | None = None,
        reviewed_snapshot: SourceReviewSnapshot | None = None,
    ) -> Self:
        return cls(
            brief_id=version.brief_id,
            brief_revision=version.brief_revision,
            canonical_requirements=list(version.canonical_requirements),
            publication=(
                ReportPublicationOut.from_document(
                    build_document(record, version, reviewed_snapshot=reviewed_snapshot)
                )
                if record is not None
                else None
            ),
            reviewed_source_snapshot=reviewed_snapshot,
            claim_ledger=ClaimLedgerOut.model_validate(build_claim_ledger(version)),
            claim_generation=version.claim_generation,
            model_routing=ModelRoutingOut.model_validate(version.model_routing)
            if version.model_routing
            else None,
            research_context=(
                ResearchContextOut.model_validate(version.research_context)
                if version.research_context is not None
                else None
            ),
            challenge=ReportChallengeOut.model_validate(version.challenge)
            if version.challenge
            else None,
            citation_checks=(
                ReportCitationChecksOut.model_validate(version.citation_checks)
                if version.citation_checks
                else None
            ),
            research=ResearchReceiptOut.model_validate(version.research)
            if version.research
            else None,
            assessment=(
                ReportAssessmentOut.model_validate(version.assessment)
                if version.assessment
                else None
            ),
            period_from=version.period_from,
            period_to=version.period_to,
            data_cutoff=version.data_cutoff,
            direction=direction_to_dict(version.direction) if version.direction else None,
            devils_advocacy=advocacy_to_dict(version.advocacy) if version.advocacy else None,
            number=version.number,
            status=version.status,
            body=body_to_dict(version.body),
            findings=findings_to_list(version.findings),
            evidence=[ReportEvidenceOut.model_validate(item) for item in version.evidence],
            quality=quality_to_dict(version.quality),
            markdown=version.markdown,
            model=version.model,
            prompt_tokens=version.prompt_tokens,
            completion_tokens=version.completion_tokens,
            latency_ms=round(version.latency_ms, 1),
            attempts=version.attempts,
            created_at=version.created_at,
        )


class ReportOut(BaseModel):
    report: ReportSummaryOut
    version: ReportVersionOut

    @classmethod
    def build(
        cls,
        record: ReportRecord,
        version: ReportVersion,
        reviewed_snapshot: SourceReviewSnapshot | None = None,
    ) -> Self:
        return cls(
            report=ReportSummaryOut.from_record(record),
            version=ReportVersionOut.from_version(version, record, reviewed_snapshot),
        )

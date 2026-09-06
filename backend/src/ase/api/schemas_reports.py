"""Request and response models for reports."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ase.api.schemas_challenge import ReportChallengeOut
from ase.api.schemas_citation_checks import ReportCitationChecksOut
from ase.api.schemas_report_assessment import ReportAssessmentOut
from ase.api.schemas_report_evidence import ReportEvidenceOut
from ase.api.schemas_research import ResearchReceiptOut
from ase.api.schemas_research_context import ResearchContextOut
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import TEMPLATES, Template
from ase.domain.advocacy import advocacy_to_dict
from ase.domain.direction import direction_to_dict
from ase.domain.events import Category
from ase.domain.report_records import (
    ReportRecord,
    ReportVersion,
    body_to_dict,
    findings_to_list,
    quality_to_dict,
)
from ase.domain.reports import ReportStatus
from ase.domain.research import ResearchFocus, ResearchMode


class ReportCreateIn(BaseModel):
    template: str = Field(min_length=1, max_length=32)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    categories: list[Category] = Field(default_factory=list, max_length=11)
    question: str | None = Field(default=None, max_length=1000)
    window_hours: int | None = Field(default=None, ge=1, le=24 * 14)
    profile_id: UUID | None = None
    devils_advocacy: bool = False
    hazard: str | None = Field(default=None, max_length=32)
    conflict: str | None = Field(default=None, max_length=64)
    plan: UUID | None = None
    team_id: UUID | None = None
    research_mode: ResearchMode | None = None
    research_languages: list[Annotated[str, Field(pattern=r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$")]] = (
        Field(default_factory=lambda: ["en"], min_length=1, max_length=8)
    )
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = Field(default=None, max_length=300)
    research_input_id: UUID | None = None
    parent_report_id: UUID | None = None

    @model_validator(mode="after")
    def research_requires_question(self) -> Self:
        if self.research_mode and (not self.question or not self.question.strip()):
            raise ValueError("On-demand research requires a question")
        if self.research_mode and self.country and self.research_focus is not ResearchFocus.GENERAL:
            raise ValueError("Country filters are unavailable for record-focused research")
        return self

    def to_request(self) -> ReportRequest:
        return ReportRequest(
            template_id=self.template.strip().lower(),
            country_iso=self.country.upper() if self.country else None,
            categories=tuple(self.categories),
            question=self.question.strip() if self.question else None,
            window_hours=self.window_hours,
            profile_id=self.profile_id,
            devils_advocacy=self.devils_advocacy,
            hazard=self.hazard.strip().lower() if self.hazard else None,
            conflict_id=self.conflict.strip().lower() if self.conflict else None,
            plan_id=self.plan,
            team_id=self.team_id,
            research_mode=self.research_mode,
            research_languages=tuple(dict.fromkeys(self.research_languages)),
            research_focus=self.research_focus,
            research_subject=self.research_subject,
            research_input_id=self.research_input_id,
            parent_report_id=self.parent_report_id,
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
    def from_version(cls, version: ReportVersion) -> Self:
        return cls(
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
    def build(cls, record: ReportRecord, version: ReportVersion) -> Self:
        return cls(
            report=ReportSummaryOut.from_record(record),
            version=ReportVersionOut.from_version(version),
        )

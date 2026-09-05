"""Generate a report: select and freeze evidence, ask the model, validate, retry once, persist."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.feeds import EventStore
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.llm import (
    LlmGateway,
    LlmGatewayError,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.application.ports.reports import ReportRepository
from ase.application.reports.prompts import compose_messages
from ase.application.reports.render import render_markdown
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import Template, template_for
from ase.domain.audit import AuditAction
from ase.domain.errors import EncryptionUnavailable, InvalidRequest, NoModelAvailable, RateLimited
from ase.domain.events import Category
from ase.domain.evidence import EvidenceItem, QualityOfInformation, quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmProfile, LlmRequest, LlmRole, LlmUsage
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import ReportBody, ReportHeader, ReportParseError, ReportStatus, parse_body
from ase.domain.users import User
from ase.domain.validation import Finding, Severity, validate_body

MAX_ATTEMPTS = 2


@dataclass(frozen=True, slots=True)
class ReportRequest:
    template_id: str
    country_iso: str | None = None
    categories: tuple[Category, ...] = ()
    question: str | None = None
    window_hours: int | None = None
    profile_id: UUID | None = None


@dataclass(slots=True)
class _Draft:
    body: ReportBody | None = None
    findings: list[Finding] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0
    attempts: int = 0


class GenerateReportUseCase:
    def __init__(
        self,
        *,
        store: EventStore,
        source_profiles: Mapping[str, SourceProfile],
        countries: CountryDirectory,
        llm_profiles: LlmProfileRepository,
        usage: LlmUsageRepository,
        cipher: SecretCipher,
        gateway: LlmGateway,
        reports: ReportRepository,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._store = store
        self._source_profiles = source_profiles
        self._countries = countries
        self._llm_profiles = llm_profiles
        self._usage = usage
        self._cipher = cipher
        self._gateway = gateway
        self._reports = reports
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, actor: User, request: ReportRequest, context: RequestContext
    ) -> tuple[ReportRecord, ReportVersion]:
        retry_after = self._limiter.hit(
            f"reports:{actor.id}", self._limits.reports_per_user, self._limits.hourly_window_seconds
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        template = self._template(request)
        profile = await self._profile(request.profile_id, template.role)
        if not self._cipher.available:
            raise EncryptionUnavailable()
        now = self._clock.now()
        window = timedelta(hours=request.window_hours or template.strategy.window_hours)
        selection = select_evidence(
            self._store,
            self._source_profiles,
            template.strategy,
            now=now,
            country_iso=request.country_iso,
            categories=request.categories,
        )
        quality = quality_of_information(selection.items, selection.flagged)
        header = ReportHeader(
            template=template.id,
            title=self._title(template, request),
            scope=self._scope(request, window),
            period_from=now - window,
            period_to=now,
            data_cutoff=now,
        )
        draft = await self._draft(profile, template, header, request, quality, selection.items)
        await self._log_usage(profile, actor, template, draft, now)
        body = draft.body or ReportBody()
        status = self._status(draft)
        markdown = render_markdown(header, body, selection.items, quality, draft.findings)
        record = ReportRecord(
            id=uuid4(),
            template=template.id,
            title=header.title,
            scope=header.scope,
            period_from=header.period_from,
            period_to=header.period_to,
            data_cutoff=header.data_cutoff,
            status=status,
            created_by=actor.id,
            created_at=now,
            latest_version=1,
        )
        version = ReportVersion(
            id=uuid4(),
            report_id=record.id,
            number=1,
            status=status,
            body=body,
            findings=tuple(draft.findings),
            evidence=selection.items,
            quality=quality,
            markdown=markdown,
            profile_id=profile.id,
            model=draft.model or profile.model,
            prompt_tokens=draft.prompt_tokens,
            completion_tokens=draft.completion_tokens,
            latency_ms=draft.latency_ms,
            attempts=draft.attempts,
            created_at=now,
        )
        await self._reports.add(record, version)
        await self._auditor.record(
            AuditAction.REPORT_GENERATED,
            actor=actor.id,
            subject=str(record.id),
            ip=context.ip,
            details={"template": template.id, "status": status.value, "attempts": draft.attempts},
        )
        await self._uow.commit()
        return record, version

    @staticmethod
    def _template(request: ReportRequest) -> Template:
        try:
            template = template_for(request.template_id)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if template.needs_country and not request.country_iso:
            raise InvalidRequest("This template needs a country.")
        if template.needs_question and not (request.question or "").strip():
            raise InvalidRequest("This template needs a question.")
        return template

    async def _profile(self, profile_id: UUID | None, role: LlmRole) -> LlmProfile:
        if profile_id is not None:
            profile = await self._llm_profiles.get(profile_id)
            if profile is None or not profile.allows(role):
                raise NoModelAvailable()
            return profile
        for candidate in await self._llm_profiles.list_all():
            if candidate.allows(role):
                return candidate
        raise NoModelAvailable()

    def _title(self, template: Template, request: ReportRequest) -> str:
        if request.question:
            return f"{template.title}: {request.question.strip()[:120]}"
        if request.country_iso:
            country = self._countries.get(request.country_iso)
            return f"{template.title}: {country.name if country else request.country_iso}"
        return f"{template.title}: global"

    @staticmethod
    def _scope(request: ReportRequest, window: timedelta) -> dict[str, Any]:
        return {
            "country": request.country_iso,
            "categories": [category.value for category in request.categories],
            "question": request.question,
            "window_hours": int(window.total_seconds() // 3600),
        }

    async def _draft(
        self,
        profile: LlmProfile,
        template: Template,
        header: ReportHeader,
        request: ReportRequest,
        quality: QualityOfInformation,
        evidence: Sequence[EvidenceItem],
    ) -> _Draft:
        draft = _Draft()
        api_key = self._cipher.decrypt(profile.api_key_encrypted)
        scope_line = self._title(template, request)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            draft.attempts = attempt
            messages = compose_messages(
                template,
                scope_line=scope_line,
                period_from=header.period_from,
                period_to=header.period_to,
                question=request.question,
                quality=quality,
                evidence=evidence,
                findings=draft.findings,
            )
            llm_request = LlmRequest(
                messages=messages,
                max_output_tokens=min(profile.max_output_tokens, template.token_budget),
                temperature=profile.temperature,
                json_schema=REPORT_BODY_SCHEMA,
                schema_name="report",
            )
            try:
                result = await self._gateway.complete(
                    profile.base_url, api_key, profile.model, llm_request
                )
            except LlmGatewayError as exc:
                draft.findings = [Finding("model", Severity.ERROR, "gateway", str(exc))]
                continue
            draft.model = result.model
            draft.prompt_tokens = (draft.prompt_tokens or 0) + (result.prompt_tokens or 0)
            draft.completion_tokens = (draft.completion_tokens or 0) + (
                result.completion_tokens or 0
            )
            draft.latency_ms += result.latency_ms
            try:
                parsed = parse_body(json.loads(result.content))
            except (ValueError, ReportParseError) as exc:
                draft.findings = [Finding("schema", Severity.ERROR, "output", f"{exc}"[:300])]
                continue
            validated = validate_body(
                parsed,
                frozenset(item.label for item in evidence),
                {item.label: item.url for item in evidence},
                confidence_ceiling=quality.confidence_ceiling,
            )
            draft.body = validated.body
            draft.findings = list(validated.findings)
            if validated.passed:
                break
        return draft

    @staticmethod
    def _status(draft: _Draft) -> ReportStatus:
        if draft.body is None:
            return ReportStatus.FAILED
        if any(f.severity is Severity.ERROR for f in draft.findings):
            return ReportStatus.NEEDS_REVIEW
        return ReportStatus.READY

    async def _log_usage(
        self, profile: LlmProfile, actor: User, template: Template, draft: _Draft, now: Any
    ) -> None:
        errors = [f.message for f in draft.findings if f.severity is Severity.ERROR]
        await self._usage.add(
            LlmUsage(
                at=now,
                profile_id=profile.id,
                user_id=actor.id,
                purpose=f"report:{template.id}",
                ok=draft.body is not None,
                latency_ms=draft.latency_ms,
                prompt_tokens=draft.prompt_tokens,
                completion_tokens=draft.completion_tokens,
                error="; ".join(errors)[:500] or None,
            )
        )

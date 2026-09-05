"""Generate a report: select and freeze evidence, ask the model, validate, retry once, persist.

Regeneration produces a further version of an existing report from the same scope, with
the previous key judgements shown to the model so it can say what changed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.feeds import EventStore
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.llm import (
    LlmGateway,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.application.ports.reports import ReportRepository
from ase.application.reports.drafting import Draft, draft_body
from ase.application.reports.render import render_markdown
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import Template, template_for
from ase.domain.audit import AuditAction
from ase.domain.errors import (
    EncryptionUnavailable,
    InvalidRequest,
    NoModelAvailable,
    NotFound,
    RateLimited,
)
from ase.domain.events import Category
from ase.domain.evidence import quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import (
    ReportBody,
    ReportHeader,
    ReportStatus,
)
from ase.domain.users import User
from ase.domain.validation import Severity


@dataclass(frozen=True, slots=True)
class ReportRequest:
    template_id: str
    country_iso: str | None = None
    categories: tuple[Category, ...] = ()
    question: str | None = None
    window_hours: int | None = None
    profile_id: UUID | None = None

    @classmethod
    def from_scope(cls, template_id: str, scope: Mapping[str, Any]) -> ReportRequest:
        categories = tuple(Category(str(c)) for c in scope.get("categories") or [])
        window = scope.get("window_hours")
        return cls(
            template_id=template_id,
            country_iso=scope.get("country") or None,
            categories=categories,
            question=scope.get("question") or None,
            window_hours=int(window) if window else None,
        )


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
        """A new report from the live evidence: version 1 of a new record."""
        template = self._template(request)
        profile = await self._prepare(actor, request.profile_id, template)
        now = self._clock.now()
        version = await self._produce(actor, template, request, profile, now, previous=None)
        record = ReportRecord(
            id=version.report_id,
            template=template.id,
            title=self._title(template, request),
            scope=self._scope(request, template),
            period_from=now - self._window(request, template),
            period_to=now,
            data_cutoff=now,
            status=version.status,
            created_by=actor.id,
            created_at=now,
            latest_version=1,
        )
        await self._reports.add(record, version)
        await self._finish(actor, record, version, context)
        return record, version

    async def regenerate(
        self, actor: User, report_id: UUID, context: RequestContext
    ) -> tuple[ReportRecord, ReportVersion]:
        """A further version of an existing report, judged against its previous judgements."""
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        previous = await self._reports.get_version(report_id, record.latest_version)
        if previous is None:
            raise NotFound()
        request = ReportRequest.from_scope(record.template, record.scope)
        template = self._template(request)
        profile = await self._prepare(actor, None, template)
        now = self._clock.now()
        version = await self._produce(
            actor, template, request, profile, now, previous=previous, report_id=record.id
        )
        record.status = version.status
        record.latest_version = version.number
        record.period_from = now - self._window(request, template)
        record.period_to = now
        record.data_cutoff = now
        await self._reports.add_version(record, version)
        await self._finish(actor, record, version, context)
        return record, version

    async def _prepare(
        self, actor: User, profile_id: UUID | None, template: Template
    ) -> LlmProfile:
        retry_after = self._limiter.hit(
            f"reports:{actor.id}", self._limits.reports_per_user, self._limits.hourly_window_seconds
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        profile = await self._profile(profile_id, template.role)
        if not self._cipher.available:
            raise EncryptionUnavailable()
        return profile

    async def _produce(
        self,
        actor: User,
        template: Template,
        request: ReportRequest,
        profile: LlmProfile,
        now: datetime,
        *,
        previous: ReportVersion | None,
        report_id: UUID | None = None,
    ) -> ReportVersion:
        window = self._window(request, template)
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
            scope=self._scope(request, template),
            period_from=now - window,
            period_to=now,
            data_cutoff=now,
        )
        earlier = previous.body.key_judgements if previous is not None else ()
        draft = await draft_body(
            self._gateway,
            profile,
            self._cipher.decrypt(profile.api_key_encrypted),
            template,
            header,
            request.question,
            quality,
            selection.items,
            earlier,
        )
        await self._log_usage(profile, actor, template, draft, now)
        body = draft.body or ReportBody()
        status = self._status(draft)
        markdown = render_markdown(header, body, selection.items, quality, draft.findings)
        return ReportVersion(
            id=uuid4(),
            report_id=report_id or uuid4(),
            number=previous.number + 1 if previous is not None else 1,
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

    async def _finish(
        self, actor: User, record: ReportRecord, version: ReportVersion, context: RequestContext
    ) -> None:
        await self._auditor.record(
            AuditAction.REPORT_GENERATED,
            actor=actor.id,
            subject=str(record.id),
            ip=context.ip,
            details={
                "template": record.template,
                "version": version.number,
                "status": version.status.value,
                "attempts": version.attempts,
            },
        )
        await self._uow.commit()

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

    @staticmethod
    def _window(request: ReportRequest, template: Template) -> timedelta:
        return timedelta(hours=request.window_hours or template.strategy.window_hours)

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

    def _scope(self, request: ReportRequest, template: Template) -> dict[str, Any]:
        return {
            "country": request.country_iso,
            "categories": [category.value for category in request.categories],
            "question": request.question,
            "window_hours": int(self._window(request, template).total_seconds() // 3600),
        }

    @staticmethod
    def _status(draft: Draft) -> ReportStatus:
        if draft.body is None:
            return ReportStatus.FAILED
        if draft.has_errors:
            return ReportStatus.NEEDS_REVIEW
        return ReportStatus.READY

    async def _log_usage(
        self, profile: LlmProfile, actor: User, template: Template, draft: Draft, now: datetime
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

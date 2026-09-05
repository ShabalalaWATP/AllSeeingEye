"""Generate a report: resolve template, profile and scope, produce a version, persist it.

Regeneration produces a further version of an existing report from the same scope, with
the previous key judgements shown to the model so it can say what changed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.feeds import EventStore
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.llm import (
    LlmGateway,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.application.ports.reports import ReportRepository
from ase.application.ports.trackers import ConflictDirectory
from ase.application.reports.production import Job, Producer
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import Template, template_for
from ase.domain.audit import AuditAction
from ase.domain.collection import CollectionPlan
from ase.domain.errors import (
    EncryptionUnavailable,
    InvalidRequest,
    NoModelAvailable,
    NotFound,
    RateLimited,
)
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.trackers import HAZARD_TITLES, Conflict, Hazard
from ase.domain.users import User

__all__ = ["GenerateReportUseCase", "ReportRequest"]


class GenerateReportUseCase:
    def __init__(
        self,
        *,
        store: EventStore,
        source_profiles: Mapping[str, SourceProfile],
        countries: CountryDirectory,
        conflicts: ConflictDirectory,
        plans: PlanRepository,
        aois: AoiRepository,
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
        backgrounds: Mapping[str, Callable[[], Awaitable[str]]] | None = None,
    ) -> None:
        self._backgrounds = dict(backgrounds or {})
        self._producer = Producer(
            store=store,
            source_profiles=source_profiles,
            cipher=cipher,
            gateway=gateway,
            usage=usage,
        )
        self._countries = countries
        self._conflicts = conflicts
        self._plans = plans
        self._aois = aois
        self._llm_profiles = llm_profiles
        self._cipher = cipher
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
        plan = await self._plan(request)
        profile = await self._prepare(actor, request.profile_id, template)
        now = self._clock.now()
        job = await self._job(actor, template, request, profile, now, plan=plan)
        version = await self._producer.produce(job, self._profile_for)
        record = ReportRecord(
            id=version.report_id,
            template=template.id,
            title=job.title,
            scope=dict(job.scope),
            period_from=now - job.window,
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
        plan = await self._plan(request)
        profile = await self._prepare(actor, None, template)
        now = self._clock.now()
        job = await self._job(
            actor,
            template,
            request,
            profile,
            now,
            previous=previous,
            report_id=record.id,
            plan=plan,
        )
        version = await self._producer.produce(job, self._profile_for)
        record.status = version.status
        record.latest_version = version.number
        record.period_from = now - job.window
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

    async def _job(
        self,
        actor: User,
        template: Template,
        request: ReportRequest,
        profile: LlmProfile,
        now: datetime,
        *,
        previous: ReportVersion | None = None,
        report_id: UUID | None = None,
        plan: CollectionPlan | None = None,
    ) -> Job:
        country = self._countries.get(request.country_iso) if request.country_iso else None
        conflict = self._conflict(request)
        hazard = self._hazard(request)
        provider = self._backgrounds.get(template.id)
        background = await provider() if provider is not None else self._background(conflict)
        aoi = await self._aois.get(plan.aoi_id) if plan is not None and plan.aoi_id else None
        if plan is not None:
            background = plan.description or None
            request = replace(request, question=request.question or plan.pirs[0].text)
        return Job(
            actor=actor,
            template=template,
            request=request,
            profile=profile,
            now=now,
            window=self._window(request, template),
            title=self._title(template, request, country, conflict, hazard, plan),
            scope=self._scope(request, template),
            country_name=country.name if country else None,
            previous=previous,
            report_id=report_id,
            bbox=conflict.bbox if conflict else (aoi.bbox if aoi else None),
            countries=conflict.countries
            if conflict
            else (plan.countries or (aoi.countries if aoi else ()) if plan else ()),
            hazard=hazard,
            terms=conflict.keywords if conflict else (plan.search_terms() if plan else ()),
            background=background,
            direction=plan.direction() if plan is not None else None,
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

    def _template(self, request: ReportRequest) -> Template:
        try:
            template = template_for(request.template_id)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if template.needs_country and not request.country_iso:
            raise InvalidRequest("This template needs a country.")
        if template.needs_question and not (request.question or "").strip() and not request.plan_id:
            raise InvalidRequest("This template needs a question.")
        if template.needs_conflict and self._conflict(request) is None:
            raise InvalidRequest("This template needs a conflict from the tracker list.")
        if template.needs_hazard and self._hazard(request) is None:
            raise InvalidRequest("This template needs a hazard from the disaster tracker.")
        return template

    async def _plan(self, request: ReportRequest) -> CollectionPlan | None:
        if request.plan_id is None:
            return None
        plan = await self._plans.get(request.plan_id)
        if plan is None or not plan.pirs:
            raise InvalidRequest("Unknown collection plan.")
        return plan

    def _conflict(self, request: ReportRequest) -> Conflict | None:
        return self._conflicts.get(request.conflict_id) if request.conflict_id else None

    @staticmethod
    def _hazard(request: ReportRequest) -> Hazard | None:
        try:
            return Hazard(request.hazard) if request.hazard else None
        except ValueError:
            return None

    @staticmethod
    def _window(request: ReportRequest, template: Template) -> timedelta:
        return timedelta(hours=request.window_hours or template.strategy.window_hours)

    async def _profile_for(self, role: LlmRole) -> LlmProfile | None:
        """The first enabled profile that plays the role, or None."""
        for candidate in await self._llm_profiles.list_all():
            if candidate.allows(role):
                return candidate
        return None

    async def _profile(self, profile_id: UUID | None, role: LlmRole) -> LlmProfile:
        if profile_id is not None:
            chosen = await self._llm_profiles.get(profile_id)
            if chosen is None or not chosen.allows(role):
                raise NoModelAvailable()
            return chosen
        profile = await self._profile_for(role)
        if profile is None:
            raise NoModelAvailable()
        return profile

    @staticmethod
    def _title(
        template: Template,
        request: ReportRequest,
        country: Any,
        conflict: Conflict | None,
        hazard: Hazard | None,
        plan: CollectionPlan | None = None,
    ) -> str:
        if plan is not None:
            return f"{template.title}: {plan.name}"
        if conflict is not None:
            return f"{template.title}: {conflict.name}"
        place = country.name if country else request.country_iso
        if hazard is not None:
            where = f" in {place}" if place else ""
            return f"{template.title}: {HAZARD_TITLES[hazard].lower()}{where}"
        if request.question:
            return f"{template.title}: {request.question.strip()[:120]}"
        if place:
            return f"{template.title}: {place}"
        return f"{template.title}: global"

    @staticmethod
    def _background(conflict: Conflict | None) -> str | None:
        if conflict is None:
            return None
        sides = ", ".join(conflict.belligerents) or "not listed"
        return f"{conflict.name} ({conflict.status}). {conflict.summary} Belligerents: {sides}."

    def _scope(self, request: ReportRequest, template: Template) -> dict[str, Any]:
        return {
            "country": request.country_iso,
            "categories": [category.value for category in request.categories],
            "question": request.question,
            "window_hours": int(self._window(request, template).total_seconds() // 3600),
            "devils_advocacy": request.devils_advocacy,
            "hazard": request.hazard,
            "conflict": request.conflict_id,
            "plan": str(request.plan_id) if request.plan_id else None,
        }

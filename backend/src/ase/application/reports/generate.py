"""Generate a report: resolve template, profile and scope, produce a version, persist it.

Regeneration produces a further version of an existing report from the same scope, with
the previous key judgements shown to the model so it can say what changed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.model_routing import ModelRouting, RoleProfiles
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.feeds import EventStore
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.llm import (
    LlmBindingRepository,
    LlmGateway,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.application.ports.map_views import MapViewRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.research import ResearchCollection
from ase.application.ports.research_inputs import ResearchInputStore
from ase.application.ports.trackers import ConflictDirectory
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.production import Job, Producer
from ase.application.reports.progress import Progress
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_inputs import ReportResearchInputs
from ase.application.reports.scope import (
    conflict_background,
    report_scope,
    report_title,
    report_window,
)
from ase.application.reports.templates import Template, template_for
from ase.domain.audit import AuditAction
from ase.domain.collection import CollectionPlan
from ase.domain.errors import (
    EncryptionUnavailable,
    InvalidRequest,
    NotFound,
    RateLimited,
)
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmProfile
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.trackers import Conflict, Hazard
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
        access: AccessPolicy,
        backgrounds: Mapping[str, Callable[[], Awaitable[str]]] | None = None,
        url_resolver: EvidenceUrlResolver | None = None,
        research: ResearchCollection | None = None,
        private_store_factory: Callable[[], EventStore] | None = None,
        research_inputs: ResearchInputStore | None = None,
        llm_bindings: LlmBindingRepository | None = None,
        map_views: MapViewRepository | None = None,
    ) -> None:
        self._backgrounds = dict(backgrounds or {})
        self._producer = Producer(
            store=store,
            source_profiles=source_profiles,
            cipher=cipher,
            gateway=gateway,
            usage=usage,
            url_resolver=url_resolver,
            research=research,
            private_store_factory=private_store_factory,
        )
        self._countries = countries
        self._conflicts = conflicts
        self._plans = plans
        self._aois = aois
        self._routing = ModelRouting(llm_profiles, llm_bindings)
        self._cipher = cipher
        self._reports = reports
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._auditor = auditor
        self._uow = uow
        self._map_origin = ReportMapOrigin(access, reports, map_views)
        self._authorisation = ReportAuthorisation(
            access, reports, plans, aois, uow, self._map_origin
        )
        self._research_inputs = ReportResearchInputs(access, reports, research_inputs)

    async def execute(
        self,
        actor: User,
        request: ReportRequest,
        context: RequestContext,
        *,
        progress: Progress | None = None,
    ) -> tuple[ReportRecord, ReportVersion]:
        """A new report from the live evidence: version 1 of a new record."""
        template = self._template(request)
        plan = await self._authorisation.prepare(actor, request)
        request = await self._map_origin.resolve(actor, request)
        inputs = await self._research_inputs.prepare(actor, request)
        routing = await self._prepare(actor, request, template)
        profile = routing.required(template.role)
        now = self._clock.now()
        job = inputs.apply(await self._job(actor, template, request, profile, now, plan=plan))
        await self._uow.rollback()
        version = await self._producer.produce(
            job,
            routing.profile_for,
            lambda: self._authorisation.finish(actor, request, None, plan, inputs.parent),
            progress=progress,
        )
        version.model_routing = routing.provenance
        record = ReportRecord(
            id=version.report_id,
            template=template.id,
            title=job.title,
            scope=dict(job.scope),
            period_from=now - job.window,
            period_to=now,
            data_cutoff=version.data_cutoff or now,
            status=version.status,
            created_by=actor.id,
            created_at=now,
            latest_version=1,
            team_id=request.team_id,
        )
        await self._reports.add(record, version)
        await self._finish(actor, record, version, context)
        return record, version

    async def regenerate(
        self,
        actor: User,
        report_id: UUID,
        context: RequestContext,
        *,
        progress: Progress | None = None,
    ) -> tuple[ReportRecord, ReportVersion]:
        """A further version of an existing report, judged against its previous judgements."""
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        request = replace(
            ReportRequest.from_scope(record.template, record.scope), team_id=record.team_id
        )
        plan = await self._authorisation.prepare(actor, request, record)
        request = await self._map_origin.resolve(actor, request, owner_id=record.created_by)
        previous = await self._reports.get_version(report_id, record.latest_version)
        if previous is None:
            raise NotFound()
        inputs = await self._research_inputs.prepare(
            actor, request, previous, owner_id=record.created_by
        )
        template = self._template(request)
        routing = await self._prepare(actor, request, template)
        profile = routing.required(template.role)
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
        job = inputs.apply(job)
        await self._uow.rollback()
        version = await self._producer.produce(
            job,
            routing.profile_for,
            lambda: self._authorisation.finish(actor, request, record, plan, inputs.parent),
            progress=progress,
        )
        version.model_routing = routing.provenance
        record.status = version.status
        record.latest_version = version.number
        record.period_from = now - job.window
        record.period_to = now
        record.data_cutoff = version.data_cutoff or now
        await self._reports.add_version(record, version)
        await self._finish(actor, record, version, context)
        return record, version

    async def _prepare(
        self, actor: User, request: ReportRequest, template: Template
    ) -> RoleProfiles:
        retry_after = self._limiter.hit(
            f"reports:{actor.id}", self._limits.reports_per_user, self._limits.hourly_window_seconds
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        routing = await self._routing.snapshot(
            team_id=request.team_id, profile_id=request.profile_id, role=template.role
        )
        if not self._cipher.available:
            raise EncryptionUnavailable()
        return routing

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
        background = await provider() if provider is not None else conflict_background(conflict)
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
            window=report_window(request, template),
            title=report_title(template, request, country, conflict, hazard, plan),
            scope=report_scope(request, template),
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

    def _conflict(self, request: ReportRequest) -> Conflict | None:
        return self._conflicts.get(request.conflict_id) if request.conflict_id else None

    @staticmethod
    def _hazard(request: ReportRequest) -> Hazard | None:
        try:
            return Hazard(request.hazard) if request.hazard else None
        except ValueError:
            return None

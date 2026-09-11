"""Resolve a frozen report scope from current template, country and collection records."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from ase.application.ports.direction import AoiRepository
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.trackers import ConflictDirectory
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import (
    conflict_background,
    report_scope,
    report_title,
    report_window,
)
from ase.application.reports.templates import Template, template_for
from ase.domain.collection import CollectionPlan
from ase.domain.errors import InvalidRequest
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.llm import LlmProfile
from ase.domain.report_records import ReportVersion
from ase.domain.research_scope import validate_research_interval
from ase.domain.trackers import Conflict, Hazard
from ase.domain.users import User


class ReportJobBuilder:
    def __init__(
        self,
        countries: CountryDirectory,
        conflicts: ConflictDirectory,
        aois: AoiRepository,
        backgrounds: Mapping[str, Callable[[], Awaitable[str]]],
    ) -> None:
        self._countries, self._conflicts, self._aois = countries, conflicts, aois
        self._backgrounds = backgrounds

    async def build(
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
        if request.research_since is not None and request.research_until is not None:
            try:
                validate_research_interval(
                    request.research_since,
                    request.research_until,
                    recorded=request.effective_time_basis is EvidenceTimeBasis.RECORDED,
                    now=now,
                )
            except ValueError as exc:
                raise InvalidRequest(str(exc)) from exc
        country = self._countries.get(request.country_iso) if request.country_iso else None
        country_names = [
            value.name if (value := self._countries.get(iso)) else iso
            for iso in request.country_isos
        ]
        conflict, hazard = self.conflict(request), self.hazard(request)
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
            country_name=", ".join(country_names) or None,
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

    def template(self, request: ReportRequest) -> Template:
        try:
            template = template_for(request.template_id)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if template.needs_country and len(request.country_isos) != 1:
            raise InvalidRequest("This template needs exactly one country.")
        if template.needs_question and not (request.question or "").strip() and not request.plan_id:
            raise InvalidRequest("This template needs a question.")
        if template.needs_conflict and self.conflict(request) is None:
            raise InvalidRequest("This template needs a conflict from the tracker list.")
        if template.needs_hazard and self.hazard(request) is None:
            raise InvalidRequest("This template needs a hazard from the disaster tracker.")
        return template

    def conflict(self, request: ReportRequest) -> Conflict | None:
        return self._conflicts.get(request.conflict_id) if request.conflict_id else None

    @staticmethod
    def hazard(request: ReportRequest) -> Hazard | None:
        try:
            return Hazard(request.hazard) if request.hazard else None
        except ValueError:
            return None

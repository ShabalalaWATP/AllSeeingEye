"""Resolve an immutable map area without importing its parent report's evidence."""

from dataclasses import replace
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports.map_views import MapViewRepository
from ase.application.ports.reports import ReportRepository
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import AREA_TEMPLATES
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.map_research_origin import MapResearchOrigin
from ase.domain.map_view_records import revision_digest
from ase.domain.research import ResearchFocus
from ase.domain.research_area import ResearchArea
from ase.domain.users import User


class ReportMapOrigin:
    def __init__(
        self, access: AccessPolicy, reports: ReportRepository, views: MapViewRepository | None
    ) -> None:
        self.access, self.reports, self.views = access, reports, views

    async def _direct(
        self, actor: User, request: ReportRequest, *, require_disclosure: bool
    ) -> None:
        if request.research_area is None:
            return
        access = await self.access.context(actor)
        access.require_create(request.team_id)
        if require_disclosure and request.disclose_area_to_provider is not True:
            raise InvalidRequest(
                "Confirm disclosure of this area and interval to selected providers."
            )

    async def resolve(
        self,
        actor: User,
        request: ReportRequest,
        *,
        owner_id: UUID | None = None,
        require_disclosure: bool = True,
    ) -> ReportRequest:
        if request.map_view_id is None and request.map_revision_id is None:
            if request.map_origin is not None:
                raise InvalidRequest("A research area needs its saved map reference.")
            await self._direct(actor, request, require_disclosure=require_disclosure)
            return request
        if self.views is None or request.map_view_id is None or request.map_revision_id is None:
            raise InvalidRequest("Choose an exact saved map revision.")
        if (
            request.research_mode is None
            or request.research_focus is not ResearchFocus.GENERAL
            or request.template_id not in AREA_TEMPLATES
            or request.parent_report_id is not None
            or request.research_input_id is not None
            or request.plan_id is not None
            or request.country_isos
            or request.conflict_id is not None
            or request.hazard is not None
            or request.categories
        ):
            raise InvalidRequest("Area research needs a standalone general research question.")
        if require_disclosure and request.disclose_area_to_provider is not True:
            raise InvalidRequest(
                "Confirm disclosure of this area and interval to selected providers."
            )
        access = await self.access.context(actor)
        view = await self.views.get(request.map_view_id)
        if view is None:
            raise NotFound()
        access.require_read(view.created_by, view.team_id)
        parent = await self.reports.get(view.report_id)
        if parent is None:
            raise NotFound()
        access.require_read(parent.created_by, parent.team_id)
        access.require_same_scope(view.created_by, view.team_id, parent.created_by, parent.team_id)
        access.require_same_scope(
            owner_id or actor.id, request.team_id, parent.created_by, parent.team_id
        )
        revision = await self.views.revision(view.id, request.map_revision_id)
        if revision is None or revision.state.aoi is None:
            raise NotFound()
        version = await self.reports.get_version(parent.id, revision.report_version_number)
        if version is None or version.id != revision.report_version_id:
            raise NotFound()
        if (
            evidence_digest(version) != revision.evidence_sha256
            or revision_digest(
                revision.state, revision.title, str(version.id), revision.evidence_sha256
            )
            != revision.content_sha256
        ):
            raise Conflict("The saved map origin failed its integrity check.")
        origin = MapResearchOrigin(
            view.id,
            revision.id,
            parent.id,
            version.id,
            version.number,
            revision.content_sha256,
            revision.evidence_sha256,
            ResearchArea(revision.state.aoi),
        )
        if request.map_origin is not None and request.map_origin != origin:
            raise Conflict("The saved map origin has changed.")
        return replace(request, map_origin=origin)

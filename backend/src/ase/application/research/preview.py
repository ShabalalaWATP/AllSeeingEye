"""Resolve private map origins for deterministic previews without external calls."""

from dataclasses import dataclass, replace
from uuid import UUID

from ase.application.ports.research import ResearchCollection
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.request import ReportRequest
from ase.domain.map_research_origin import MapResearchOrigin
from ase.domain.research import ResearchQuery
from ase.domain.research_plan import ResearchPlan
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class ResearchPreview:
    plan: ResearchPlan
    map_origin: MapResearchOrigin | None


class PreviewResearchPlan:
    def __init__(self, research: ResearchCollection, origins: ReportMapOrigin) -> None:
        self.research, self.origins = research, origins

    async def execute(
        self,
        actor: User,
        query: ResearchQuery,
        *,
        map_view_id: UUID | None = None,
        map_revision_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> ResearchPreview:
        request = ReportRequest(
            "ask",
            question=query.question,
            research_mode=query.mode,
            research_focus=query.focus,
            country_iso=query.country_iso,
            team_id=team_id,
            map_view_id=map_view_id,
            map_revision_id=map_revision_id,
        )
        # Preview only reads authorised local state. It neither grants nor records
        # consent: report collection still requires its own explicit disclosure.
        resolved = await self.origins.resolve(actor, request, require_disclosure=False)
        origin = resolved.map_origin
        planned = replace(query, area=origin.area if origin else None)
        return ResearchPreview(self.research.plan(planned), origin)

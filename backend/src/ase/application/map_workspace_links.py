"""Linked-record checks for live views and ops-room playlists.

A view may name one collection plan filter; a playlist names live views and saved areas.
Every linked record must be readable now and share the document's personal owner or team,
even for administrators. Runs inside the caller's locked transaction.
"""

from typing import Any
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.map_workspace import MapWorkspaceRepository
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.live_views import playlist_links, view_plan
from ase.domain.map_workspace import WorkspaceKind


class MapWorkspaceLinks:
    def __init__(
        self, documents: MapWorkspaceRepository, aois: AoiRepository, plans: PlanRepository
    ) -> None:
        self.documents, self.aois, self.plans = documents, aois, plans

    async def check(
        self,
        access: AccessContext,
        kind: WorkspaceKind,
        payload: dict[str, Any],
        created_by: UUID,
        team_id: UUID | None,
    ) -> None:
        if kind == "live_view":
            plan_id = view_plan(payload)
            if plan_id is not None:
                plan = await self.plans.get(plan_id)
                if plan is None:
                    raise NotFound()
                access.require_same_scope(created_by, team_id, plan.created_by, plan.team_id)
        elif kind == "ops_playlist":
            for entry_kind, entry_id in playlist_links(payload):
                if entry_kind == "area":
                    await self._area(access, entry_id, created_by, team_id)
                    continue
                view = await self.documents.get(entry_id)
                if view is None:
                    raise NotFound()
                access.require_same_scope(created_by, team_id, view.created_by, view.team_id)
                if view.kind != "live_view":
                    raise InvalidRequest("Playlist entries must be saved live views or areas.")

    async def _area(
        self, access: AccessContext, area_id: UUID, created_by: UUID, team_id: UUID | None
    ) -> None:
        area = await self.aois.get(area_id)
        if area is None:
            raise NotFound()
        access.require_same_scope(created_by, team_id, area.created_by, area.team_id)

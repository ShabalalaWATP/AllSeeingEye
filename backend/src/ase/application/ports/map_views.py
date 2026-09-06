"""Scoped immutable map revisions. Callers hold the administration write guard."""

from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.map_views import MapView, MapViewPage, MapViewRevision


class MapViewRepository(Protocol):
    async def get(self, view_id: UUID) -> MapView | None: ...
    async def revision(self, view_id: UUID, revision_id: UUID) -> MapViewRevision | None: ...
    async def list_visible(
        self, visibility: Visibility, report_id: UUID, limit: int, offset: int
    ) -> MapViewPage: ...
    async def scope_usage(self, owner_id: UUID, team_id: UUID | None) -> tuple[int, int]:
        """All retained views and revision bytes in scope, including archived views."""
        ...

    async def create(self, view: MapView, revision: MapViewRevision) -> None: ...
    async def append(self, revision: MapViewRevision, base_revision_id: UUID) -> bool:
        """Atomically append and advance latest only if base still matches, else false."""
        ...

    async def archive(self, view_id: UUID) -> None: ...
    async def delete_for_report(self, report_id: UUID) -> None:
        """Explicit lifecycle cleanup, also safe when SQLite foreign keys are disabled."""
        ...

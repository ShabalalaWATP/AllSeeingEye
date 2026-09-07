"""Admission and fresh authorisation around untrusted image decoding and ZIP creation."""

import asyncio
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.ports.map_image import MapImageOptions, MapImageRenderer
from ase.application.research.map_views import SavedMapViews
from ase.domain.errors import Conflict, RateLimited, Unauthenticated
from ase.domain.map_views import MapView, MapViewRevision
from ase.domain.report_documents import ReportFile

_MAP_IMAGE_SLOTS = threading.BoundedSemaphore(2)


class ExportMapImage:
    def __init__(self, views: SavedMapViews, renderer: MapImageRenderer) -> None:
        self.views, self.renderer = views, renderer
        self.task: asyncio.Task[bytes] | None = None

    @contextmanager
    def admission(self) -> Iterator[None]:
        """The HTTP route enters before retaining any request bytes."""
        if not _MAP_IMAGE_SLOTS.acquire(blocking=False):
            raise RateLimited(5)
        try:
            yield
        finally:
            if self.task is not None and not self.task.done():
                self.task.add_done_callback(lambda _: _MAP_IMAGE_SLOTS.release())
            else:
                _MAP_IMAGE_SLOTS.release()

    async def resolve(
        self, claims: AccessClaims, view_id: UUID, revision_id: UUID
    ) -> tuple[MapView, MapViewRevision]:
        return await self.views.get(claims, view_id, revision_id)

    async def execute(
        self,
        claims: AccessClaims,
        selected: tuple[MapView, MapViewRevision],
        options: MapImageOptions,
    ) -> ReportFile:
        view, revision = selected
        received_at = self.views.clock.now()
        self.task = asyncio.create_task(
            asyncio.to_thread(self.renderer.render, view, revision, options, received_at)
        )
        self.task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        content = await asyncio.shield(self.task)
        # End any request snapshot before reading current account/membership and anchor.
        await self.views.uow.rollback()
        current_view, current_revision = await self.views.get(claims, view.id, revision.id)
        if (
            current_view.report_id != view.report_id
            or current_view.created_by != view.created_by
            or current_view.team_id != view.team_id
            or current_revision != revision
        ):
            raise Conflict("The saved map export anchor has changed.")
        if claims.expires_at <= self.views.clock.now():
            raise Unauthenticated("The session has ended. Sign in again.")
        # No awaited work after the last authority and token-expiry checks.
        return ReportFile(content, "application/zip", f"map-{view.id}-{revision.id}.zip")

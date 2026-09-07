"""Wire session lifetimes into the bounded application observation runner."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ase.application.reports.monitor_observation import observe
from ase.application.reports.monitor_runner import AnnotationMonitorWorker

if TYPE_CHECKING:
    from ase.container import Container


def build_annotation_monitor_worker(container: Container) -> AnnotationMonitorWorker:
    async def due(limit: int, after: UUID | None) -> list[UUID]:
        async with container.session_factory() as session:
            return await container.annotation_monitors(session).repository.due(limit, after)

    async def process(key: UUID) -> bool:
        async with container.session_factory() as session:
            return await observe(container.annotation_monitors(session), key)

    return AnnotationMonitorWorker(due, process)

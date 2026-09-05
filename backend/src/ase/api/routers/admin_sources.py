"""Source registry and health (admin only)."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import AdminUser, ContainerDep
from ase.api.schemas_events import SourceHealthOut, SourceOut, SourcesOut

router = APIRouter(prefix="/admin/sources", tags=["admin"])


@router.get("")
async def list_sources(admin: AdminUser, container: ContainerDep) -> SourcesOut:
    items = [
        SourceOut.from_spec(connector.spec, container.health.get(connector.spec.id))
        for connector in container.scheduler.connectors
    ]
    return SourcesOut(items=items)


@router.post("/{source_id}/reset")
async def reset_source(
    source_id: str, admin: AdminUser, container: ContainerDep
) -> SourceHealthOut:
    container.scheduler.resume(source_id)
    return SourceHealthOut.from_health(container.health.get(source_id))

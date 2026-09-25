"""What this deployment offers beyond the always-on features (keyed services and the like)."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_geo import CapabilitiesOut
from ase.application.ports.tiles import OS_LAYERS

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("")
async def capabilities(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> CapabilitiesOut:
    configured = container.tiles.configured
    return CapabilitiesOut(
        os_maps=configured,
        os_layers=sorted(OS_LAYERS) if configured else [],
        ai_research=await container.research_readiness(session).available(user.id),
    )

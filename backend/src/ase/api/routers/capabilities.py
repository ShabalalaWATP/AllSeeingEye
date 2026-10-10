"""What this deployment offers beyond the always-on features (keyed services and the like)."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_geo import CapabilitiesOut
from ase.api.schemas_source_licences import SourceLicenceOut
from ase.application.ports.tiles import OS_LAYERS
from ase.domain.map_licences import MAP_SOURCE_IDS

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("")
async def capabilities(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> CapabilitiesOut:
    configured = container.tiles.configured and container.source_licences.allowed("map:os_maps")
    ids = (*MAP_SOURCE_IDS, *(f"camera:{source.id}" for source in container.cameras.sources))
    return CapabilitiesOut(
        os_maps=configured,
        os_layers=sorted(OS_LAYERS) if configured else [],
        ai_research=await container.research_readiness(session).available(user.id),
        commercial_use=container.source_licences.commercial_use,
        source_licences={
            source_id: SourceLicenceOut.model_validate(
                container.source_licences.decision(source_id)
            )
            for source_id in ids
        },
    )

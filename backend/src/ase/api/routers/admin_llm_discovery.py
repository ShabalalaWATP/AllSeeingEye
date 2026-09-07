"""Administrator discovery before a draft profile is saved or tested."""

from fastapi import APIRouter

from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, SessionDep
from ase.api.schemas_llm import LlmModelsOut
from ase.api.schemas_llm_discovery import DraftModelDiscoveryIn

router = APIRouter(prefix="/admin/llm", tags=["admin"])


@router.post("/models/discover")
async def discover_draft_models(
    body: DraftModelDiscoveryIn,
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
) -> LlmModelsOut:
    models = await container.discover_draft_models(session).execute(claims, body.to_input())
    return LlmModelsOut(models=list(models))

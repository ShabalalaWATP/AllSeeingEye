"""Account-visible AI allowance status."""

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_ai_usage import AiUsageSummaryPageOut

router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])


@router.get("/me")
async def my_ai_usage(
    user: CurrentUser, session: SessionDep, container: ContainerDep, response: Response
) -> AiUsageSummaryPageOut:
    response.headers["Cache-Control"] = "no-store"
    usage = await container.ai_usage_views(session).mine(user)
    return AiUsageSummaryPageOut.from_account(usage)

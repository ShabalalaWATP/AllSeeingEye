"""Account-visible AI allowance status."""

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_ai_usage import AiUsageSummaryOut, AiUsageSummaryPageOut

router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])


@router.get("/me")
async def my_ai_usage(
    user: CurrentUser, container: ContainerDep, response: Response
) -> AiUsageSummaryPageOut:
    response.headers["Cache-Control"] = "no-store"
    summaries = await container.ai_usage_accounting.summaries(user.id)
    return AiUsageSummaryPageOut(items=[AiUsageSummaryOut.from_summary(item) for item in summaries])

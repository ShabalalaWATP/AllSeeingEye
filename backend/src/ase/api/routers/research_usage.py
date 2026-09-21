"""Read individual allowances and administer research levels without changing account roles."""

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.ai_usage_guard import AiUsageMutationAdmin
from ase.api.deps import AdminUser, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_research_usage import (
    ResearchAllowanceOut,
    ResearchTierIn,
    ResearchTierOut,
    ResearchUsagePageOut,
    UserResearchAllowanceOut,
)
from ase.domain.research_usage import TIERS

router = APIRouter(tags=["research-usage"])


@router.get("/research-usage/me")
async def my_allowance(
    user: CurrentUser, session: SessionDep, container: ContainerDep, response: Response
) -> ResearchAllowanceOut:
    response.headers["Cache-Control"] = "no-store"
    result = await container.research_usage(session).me(user)
    return ResearchAllowanceOut.from_allowance(result)


@router.get("/admin/research-usage")
async def all_allowances(
    admin: AdminUser, session: SessionDep, container: ContainerDep, response: Response
) -> ResearchUsagePageOut:
    response.headers["Cache-Control"] = "no-store"
    rows = await container.research_usage(session).list_users(admin)
    return ResearchUsagePageOut(
        tiers=[ResearchTierOut(**asdict(tier)) for tier in TIERS],
        items=[UserResearchAllowanceOut(user_id=user_id, **asdict(row)) for user_id, row in rows],
    )


@router.put("/admin/users/{user_id}/research-tier")
async def assign_tier(
    user_id: UUID,
    body: ResearchTierIn,
    admin: AiUsageMutationAdmin,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> UserResearchAllowanceOut:
    response.headers["Cache-Control"] = "no-store"
    result = await container.research_usage(session).assign(
        admin, user_id, body.tier, body.expected_revision, context
    )
    return UserResearchAllowanceOut(user_id=user_id, **asdict(result))

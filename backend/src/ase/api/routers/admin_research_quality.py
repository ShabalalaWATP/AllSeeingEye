"""Administrator research-quality scorecard (MFA-verified administrator sessions only)."""

from typing import Annotated

from fastapi import APIRouter, Query, Response
from pydantic import AfterValidator

from ase.api.deps import AdminUser, ContainerDep, SessionDep
from ase.api.schemas_research_quality import ResearchQualityOut
from ase.api.session_fence import FenceDep
from ase.container.research_quality import research_quality
from ase.domain.research_quality import QUALITY_WINDOWS

router = APIRouter(prefix="/admin/research-quality", tags=["admin"])


def _window(value: int) -> int:
    if value not in QUALITY_WINDOWS:
        raise ValueError("Choose a 7, 30, 90 or 365 day window.")
    return value


Window = Annotated[
    int, Query(description="Days to look back: 7, 30, 90 or 365."), AfterValidator(_window)
]


@router.get("")
async def get_research_quality(
    admin: AdminUser,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    window_days: Window = 90,
) -> ResearchQualityOut:
    await fence.confirm(session=session, admin_only=True)
    result = await research_quality(container, session).scorecard(admin, window_days)
    response.headers["Cache-Control"] = "private, no-store"
    return await fence.release(
        ResearchQualityOut.model_validate(result), session=session, admin_only=True
    )

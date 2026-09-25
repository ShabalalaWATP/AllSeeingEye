"""Authenticated cyber observations, historical actor references and report admission."""

from fastapi import APIRouter, Response

from ase.adapters.feeds.radar_attack_trends import SPEC as RADAR_ATTACK_SPEC
from ase.adapters.feeds.radar_attack_trends import RadarAttackSnapshot
from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_cyber import (
    CyberActorCatalogueOut,
    CyberActorsOut,
    CyberBriefingOut,
    CyberSnapshotOut,
    RadarAttackSnapshotOut,
)
from ase.api.schemas_report_jobs import public_job
from ase.api.session_fence import FenceDep
from ase.domain.cyber import ACTOR_REFERENCE_SOURCE_ID, CyberWindowDays
from ase.domain.errors import RateLimited

router = APIRouter(prefix="/cyber", tags=["cyber"])


@router.get("/radar-attacks")
async def radar_attack_trends(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> RadarAttackSnapshotOut:
    retry = container.limiter.hit(f"cyber-radar:{user.id}", 30, 60)
    if retry is not None:
        raise RateLimited(retry)
    enabled = await container.source_admission.enabled(RADAR_ATTACK_SPEC.id)
    snapshot = (
        await container.radar_attack_trends.read()
        if enabled
        else RadarAttackSnapshot("disabled", None, ())
    )
    async with container.source_admission.guard():
        if not await container.source_admission.enabled(RADAR_ATTACK_SPEC.id):
            snapshot = RadarAttackSnapshot("disabled", None, ())
        await fence.confirm()
        fence.assert_live()
        response.headers["Cache-Control"] = "private, no-store"
        return RadarAttackSnapshotOut.model_validate(snapshot)


@router.get("")
async def cyber_snapshot(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
    days: CyberWindowDays = CyberWindowDays.TWO,
) -> CyberSnapshotOut:
    selected = await container.cyber.read(days)
    async with container.source_admission.guard():
        result = await container.cyber.release(selected)
        await fence.confirm()
        fence.assert_live()
        response.headers["Cache-Control"] = "private, no-store"
        return CyberSnapshotOut.model_validate(result)


@router.get("/actors")
async def cyber_actors(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> CyberActorsOut:
    # This is a local packaged reference. Source controls still govern release.
    catalogue = container.cyber_actors
    async with container.source_admission.guard():
        available = await container.source_admission.enabled(ACTOR_REFERENCE_SOURCE_ID)
        await fence.confirm()
        fence.assert_live()
        response.headers["Cache-Control"] = "private, no-store"
        return CyberActorsOut(
            available=available,
            catalogue=CyberActorCatalogueOut.model_validate(catalogue) if available else None,
            coverage_note=(
                catalogue.limitations
                if available
                else "The actor reference source is disabled. No reference records are released."
            ),
        )


@router.post("/briefing", status_code=202)
async def cyber_briefing(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
    days: CyberWindowDays = CyberWindowDays.TWO,
) -> CyberBriefingOut:
    result = await container.cyber_briefing(session, days).ensure(
        user,
        context,
        check_session=fence.confirm,
    )
    response.headers["Cache-Control"] = "private, no-store"
    fence.assert_live()
    return CyberBriefingOut(
        job=public_job(result.job),
        next_refresh_at=result.next_refresh_at,
        coverage_note=result.coverage_note,
        window_days=days,
        period_from=result.job["period_from"],
        period_to=result.job["period_to"],
    )

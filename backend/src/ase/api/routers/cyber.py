"""Authenticated cyber observations, historical actor references and report admission."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_cyber import (
    CyberActorCatalogueOut,
    CyberActorsOut,
    CyberBriefingOut,
    CyberSnapshotOut,
)
from ase.api.schemas_report_jobs import public_job
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.domain.cyber import ACTOR_REFERENCE_SOURCE_ID, CyberWindowDays

router = APIRouter(prefix="/cyber", tags=["cyber"])


@router.get("")
async def cyber_snapshot(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    response: Response,
    days: CyberWindowDays = CyberWindowDays.TWO,
) -> CyberSnapshotOut:
    selected = await container.cyber.read(days)
    async with container.source_admission.guard():
        result = await container.cyber.release(selected)
        await validate_request_session(container, claims)
        validate_request_expiry(container, claims)
        response.headers["Cache-Control"] = "private, no-store"
        return CyberSnapshotOut.model_validate(result)


@router.get("/actors")
async def cyber_actors(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    response: Response,
) -> CyberActorsOut:
    # This is a local packaged reference. Source controls still govern release.
    catalogue = container.cyber_actors
    async with container.source_admission.guard():
        available = await container.source_admission.enabled(ACTOR_REFERENCE_SOURCE_ID)
        await validate_request_session(container, claims)
        validate_request_expiry(container, claims)
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
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
    days: CyberWindowDays = CyberWindowDays.TWO,
) -> CyberBriefingOut:
    result = await container.cyber_briefing(session, days).ensure(
        user,
        context,
        check_session=lambda: validate_request_session(container, claims),
    )
    response.headers["Cache-Control"] = "private, no-store"
    validate_request_expiry(container, claims)
    return CyberBriefingOut(
        job=public_job(result.job),
        next_refresh_at=result.next_refresh_at,
        coverage_note=result.coverage_note,
        window_days=days,
        period_from=result.job["period_from"],
        period_to=result.job["period_to"],
    )

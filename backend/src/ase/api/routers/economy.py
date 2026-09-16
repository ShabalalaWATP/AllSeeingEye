"""Authenticated, fixed public economic series. This GET never invokes a model."""

from fastapi import APIRouter, Response

from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_economy import EconomySnapshotOut
from ase.api.schemas_economy_explainer import EconomyExplainerOut, explainer_out
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.auditing import Auditor
from ase.domain.audit import AuditAction
from ase.domain.errors import RateLimited

router = APIRouter(prefix="/economy", tags=["economy"])


@router.get("")
async def economy(
    user: CurrentUser, claims: ClaimsDep, container: ContainerDep, response: Response
) -> EconomySnapshotOut:
    retry = container.limiter.hit(f"economy:{user.id}", 30, 60)
    if retry is not None:
        raise RateLimited(retry)
    snapshot = await container.economy.snapshot()
    # Public HTTP work is complete before taking the activation/release lock.
    async with container.source_admission.guard():
        visible = await container.economy.refilter(snapshot)
        await validate_request_session(container, claims)
        validate_request_expiry(container, claims)
        response.headers["Cache-Control"] = "private, no-store"
        return EconomySnapshotOut.model_validate(visible)


@router.get("/explainer")
async def economy_explainer(
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> EconomyExplainerOut:
    """Serve the shared cached explainer, generating only when the cadence allows it."""
    retry = container.limiter.hit(f"economy-explainer:{user.id}", 30, 60)
    if retry is not None:
        raise RateLimited(retry)
    view = await container.economy_explainer(session).read(allow_generation=True)
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return explainer_out(view)


@router.post("/explainer/refresh")
async def refresh_economy_explainer(
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> EconomyExplainerOut:
    """An administrator forces one regeneration; the attempt is always audited."""
    retry = container.limiter.hit(f"economy-explainer-refresh:{admin.id}", 3, 3600)
    if retry is not None:
        raise RateLimited(retry)
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    view = await container.economy_explainer(session).refresh()
    repos = container.repositories(session)
    await Auditor(repos.audit, container.clock).record(
        AuditAction.ECONOMY_EXPLAINER_REFRESHED,
        actor=admin.id,
        subject="economy_explainer",
        ip=context.ip,
        details={"status": view.status, "stale": view.stale},
    )
    await repos.uow.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return explainer_out(view)

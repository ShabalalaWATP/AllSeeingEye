"""Authenticated, fixed public economic series. This GET never invokes a model."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_economy import EconomySnapshotOut
from ase.api.session_guard import validate_request_expiry, validate_request_session
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

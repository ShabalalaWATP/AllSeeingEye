"""Authenticated recovery-code management."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.mfa_schemas import MfaPasswordIn, MfaPendingOut
from ase.api.recovery_schemas import RecoveryCodesOut, RecoveryGenerateIn, RecoveryStatusOut
from ase.domain.mfa import MfaMethod, MfaPurpose

router = APIRouter(prefix="/auth/mfa/recovery", tags=["auth"])


@router.get("")
async def status(
    actor: CurrentUser, session: SessionDep, container: ContainerDep, response: Response
) -> RecoveryStatusOut:
    remaining, available = await container.recovery_codes(session).status(actor)
    response.headers["Cache-Control"] = "no-store"
    return RecoveryStatusOut(remaining=remaining, available=available)


@router.post("/challenge")
async def challenge(
    body: MfaPasswordIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> MfaPendingOut:
    result = await container.mfa_management(session).begin(
        actor, body.password, MfaPurpose.RECOVERY_CODES, context
    )
    response.headers["Cache-Control"] = "no-store"
    return MfaPendingOut.from_pending(result)


@router.post("/generate")
async def generate(
    body: RecoveryGenerateIn,
    actor: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> RecoveryCodesOut:
    codes = await container.recovery_codes(session).generate(
        actor,
        claims,
        body.password,
        MfaMethod(body.method),
        body.code,
        body.challenge_token,
        context,
    )
    response.headers["Cache-Control"] = "no-store"
    return RecoveryCodesOut(codes=codes)

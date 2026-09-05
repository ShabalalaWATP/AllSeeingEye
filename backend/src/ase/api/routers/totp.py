"""Authenticated administrator management of their own TOTP second factor."""

from fastapi import APIRouter, Response

from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.totp_schemas import (
    TotpConfirmIn,
    TotpDisableIn,
    TotpEnrolIn,
    TotpEnrolOut,
    TotpStatusOut,
)

router = APIRouter(prefix="/auth/totp", tags=["auth"])


@router.get("")
async def status(actor: AdminUser, session: SessionDep, container: ContainerDep) -> TotpStatusOut:
    enabled, available = await container.totp(session).status(actor)
    return TotpStatusOut(enabled=enabled, available=available)


@router.post("/enrol")
async def enrol(
    body: TotpEnrolIn,
    response: Response,
    actor: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TotpEnrolOut:
    result = await container.totp(session).begin(actor, body.password, context)
    response.headers["Cache-Control"] = "no-store"
    return TotpEnrolOut(secret=result.secret, provisioning_uri=result.provisioning_uri)


@router.post("/confirm", status_code=204)
async def confirm(
    body: TotpConfirmIn,
    actor: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.totp(session).confirm(actor, body.code, context)
    return Response(status_code=204)


@router.post("/disable", status_code=204)
async def disable(
    body: TotpDisableIn,
    actor: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.totp(session).disable(actor, body.password, body.code, context)
    return Response(status_code=204)

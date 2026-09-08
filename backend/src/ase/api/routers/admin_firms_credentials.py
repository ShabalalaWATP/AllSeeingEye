"""Administrator-only encrypted FIRMS connection workflow."""

from fastapi import APIRouter

from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_firms_credentials import (
    FirmsConfirmIn,
    FirmsConnectionOut,
    FirmsConnectionTestOut,
    FirmsDraftIn,
    FirmsRevisionIn,
)

router = APIRouter(prefix="/admin/sources/firms_viirs_noaa20/connection", tags=["admin"])


@router.get("")
async def status(
    admin: AdminUser, claims: ClaimsDep, container: ContainerDep, session: SessionDep
) -> FirmsConnectionOut:
    return FirmsConnectionOut.model_validate(
        await container.admin_firms_credentials(session).get(claims)
    )


@router.put("/draft")
async def draft(
    body: FirmsDraftIn,
    admin: AdminUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> FirmsConnectionOut:
    return FirmsConnectionOut.model_validate(
        await container.admin_firms_credentials(session).draft(
            claims, body.api_key.get_secret_value(), body.expected_revision, context
        )
    )


@router.post("/test")
async def test(
    body: FirmsRevisionIn,
    admin: AdminUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> FirmsConnectionTestOut:
    return FirmsConnectionTestOut.model_validate(
        await container.admin_firms_credentials(session).test(
            claims, body.expected_revision, context
        )
    )


@router.post("/confirm")
async def confirm(
    body: FirmsConfirmIn,
    admin: AdminUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> FirmsConnectionOut:
    return FirmsConnectionOut.model_validate(
        await container.admin_firms_credentials(session).confirm(
            claims, body.expected_revision, body.test_generation, context
        )
    )


@router.delete("")
async def clear(
    body: FirmsRevisionIn,
    admin: AdminUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> FirmsConnectionOut:
    return FirmsConnectionOut.model_validate(
        await container.admin_firms_credentials(session).clear(
            claims, body.expected_revision, context
        )
    )

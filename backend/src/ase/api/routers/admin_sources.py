"""Source registry and health (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Response

from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_events import SourceHealthOut, SourceOut, SourcesOut
from ase.api.schemas_source_controls import SourceActivationIn, SourceTestOut

router = APIRouter(prefix="/admin/sources", tags=["admin"])


@router.get("")
async def list_sources(
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SourcesOut:
    response.headers["Cache-Control"] = "no-store"
    items = await container.admin_source_controls(session).list(claims)
    return SourcesOut(
        items=[
            SourceOut.from_spec(item.spec, item.health).model_copy(
                update={
                    "enabled": item.enabled,
                    "test_available": item.test_available,
                    "environment_disabled": item.environment_disabled,
                }
            )
            for item in items
        ]
    )


@router.patch("/{source_id}/activation", status_code=204)
async def activate_source(
    source_id: str,
    body: SourceActivationIn,
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.admin_source_controls(session).activate(
        claims, source_id, body.enabled, context
    )
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/{source_id}/test", response_model=SourceTestOut)
async def test_source(
    source_id: str,
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> SourceTestOut:
    response.headers["Cache-Control"] = "no-store"
    return SourceTestOut.model_validate(
        await container.admin_source_controls(session).test(claims, source_id, context)
    )


@router.post("/{source_id}/reset")
async def reset_source(
    source_id: str,
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> SourceHealthOut:
    health = await container.admin_source_controls(session).reset(claims, source_id, context)
    return SourceHealthOut.from_health(health)

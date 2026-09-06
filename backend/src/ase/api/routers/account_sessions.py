"""Bearer-authorised personal session controls."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.cookies import clear_session_cookies
from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_account_sessions import AccountSessionsOut

router = APIRouter(prefix="/me/sessions", tags=["me"])


@router.get("", response_model=AccountSessionsOut)
async def list_sessions(
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> AccountSessionsOut:
    response.headers["Cache-Control"] = "no-store"
    return AccountSessionsOut.model_validate(await container.account_sessions(session).list(claims))


@router.post("/revoke-others", status_code=204)
async def revoke_other_sessions(
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.account_sessions(session).revoke_others(claims, context)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.delete("/{family_id}", status_code=204)
async def revoke_session(
    family_id: UUID,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.account_sessions(session).revoke(claims, family_id, context)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    if family_id == claims.family_id:
        clear_session_cookies(response, container.settings)
    return response

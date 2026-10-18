"""Self-service changes for the account identified by the bearer token."""

from fastapi import APIRouter, Response

from ase.api.account_schemas import ChangePasswordIn
from ase.api.cookies import clear_session_cookies
from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas import TermsAcceptanceIn, TermsStatusOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/me", tags=["me"])


@router.post("/password", status_code=204)
async def change_password(
    body: ChangePasswordIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    # As with TOTP management, authorisation requires an explicit bearer token;
    # ambient cookies alone never authorise this write.
    await container.change_password(session).execute(
        actor,
        body.current_password,
        body.new_password,
        context,
        body.totp_code,
        body.mfa_challenge_token,
        body.mfa_code,
    )
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    clear_session_cookies(response, container.settings)
    return response


@router.post("/terms-acceptance")
async def accept_terms(
    body: TermsAcceptanceIn,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    fence: FenceDep,
    response: Response,
) -> TermsStatusOut:
    # Records acceptance of the version the reader was shown; repeats change nothing.
    status = await container.accept_terms(session).execute(claims, body.version, context)
    response.headers["Cache-Control"] = "no-store"
    return await fence.release(TermsStatusOut.from_status(status))

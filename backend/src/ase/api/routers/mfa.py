"""Restricted public MFA challenges and authenticated personal factor management."""

from fastapi import APIRouter, Response

from ase.api.cookies import clear_session_cookies, set_session_cookies
from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.mfa_schemas import (
    MfaChallengeIn,
    MfaConfirmIn,
    MfaPasswordIn,
    MfaPendingOut,
    MfaStatusOut,
    MfaVerifyIn,
)
from ase.api.schemas import TokenResponse
from ase.api.totp_schemas import TotpEnrolOut
from ase.domain.mfa import MfaPurpose
from ase.domain.users import Role

router = APIRouter(prefix="/auth/mfa", tags=["auth"])


@router.get("")
async def status(actor: CurrentUser, session: SessionDep, container: ContainerDep) -> MfaStatusOut:
    mfa = container.mfa(session)
    return MfaStatusOut(
        methods=list(await mfa.methods(actor)),
        available_methods=list(mfa.available_methods()),
        required=actor.role is Role.ADMIN,
    )


@router.post("/verify")
async def verify(
    body: MfaVerifyIn,
    response: Response,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TokenResponse:
    auth = await container.mfa(session).verify(
        body.challenge_token, body.method, body.code, context
    )
    response.headers["Cache-Control"] = "no-store"
    set_session_cookies(response, auth, container.settings)
    return TokenResponse.from_session(auth)


@router.post("/email")
async def email(
    body: MfaChallengeIn,
    response: Response,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MfaPendingOut:
    result = await container.mfa(session).send_email(body.challenge_token, context)
    response.headers["Cache-Control"] = "no-store"
    return MfaPendingOut.from_pending(result)


@router.post("/enrol-app")
async def enrol_app(
    body: MfaChallengeIn,
    response: Response,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TotpEnrolOut:
    result = await container.mfa(session).enrol_app(body.challenge_token, context)
    response.headers["Cache-Control"] = "no-store"
    return TotpEnrolOut(secret=result.secret, provisioning_uri=result.provisioning_uri)


@router.post("/email/enrol")
async def enrol_email(
    body: MfaPasswordIn,
    response: Response,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MfaPendingOut:
    result = await container.mfa_management(session).begin(
        actor, body.password, MfaPurpose.EMAIL_ENROL, context
    )
    response.headers["Cache-Control"] = "no-store"
    return MfaPendingOut.from_pending(result)


@router.post("/email/enrol/confirm", status_code=204)
async def confirm_email(
    body: MfaConfirmIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.mfa_management(session).confirm(
        actor, body.challenge_token, body.code, MfaPurpose.EMAIL_ENROL, context
    )
    response = Response(status_code=204)
    clear_session_cookies(response, container.settings)
    return response


@router.post("/email/disable")
async def disable_email(
    body: MfaPasswordIn,
    response: Response,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MfaPendingOut:
    result = await container.mfa_management(session).begin(
        actor, body.password, MfaPurpose.EMAIL_DISABLE, context
    )
    response.headers["Cache-Control"] = "no-store"
    return MfaPendingOut.from_pending(result)


@router.post("/email/disable/confirm", status_code=204)
async def confirm_disable(
    body: MfaConfirmIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.mfa_management(session).confirm(
        actor, body.challenge_token, body.code, MfaPurpose.EMAIL_DISABLE, context
    )
    response = Response(status_code=204)
    clear_session_cookies(response, container.settings)
    return response


@router.post("/password-change")
async def password_change(
    body: MfaPasswordIn,
    response: Response,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MfaPendingOut:
    result = await container.mfa_management(session).begin(
        actor, body.password, MfaPurpose.PASSWORD_CHANGE, context
    )
    response.headers["Cache-Control"] = "no-store"
    return MfaPendingOut.from_pending(result)

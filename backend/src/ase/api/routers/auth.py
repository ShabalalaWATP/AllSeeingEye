"""Public authentication endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status

from ase.api.cookies import REFRESH_COOKIE, clear_session_cookies, set_session_cookies
from ase.api.deps import ContainerDep, ContextDep, SessionDep, require_csrf
from ase.api.mfa_schemas import MfaPendingOut
from ase.api.schemas import (
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    RequestAccountIn,
    SetPasswordIn,
    TokenResponse,
)
from ase.domain.mfa import PendingMfa
from ase.domain.tokens import TokenPurpose
from ase.domain.users import normalise_email

router = APIRouter(prefix="/auth", tags=["auth"])

REQUEST_ACCOUNT_MESSAGE = "If the address is eligible, an administrator will review the request."
FORGOT_MESSAGE = (
    "If the address is registered, check your email for a reset link. "
    "You can request another if it does not arrive."
)
FORGOT_RESPONSE_FLOOR_SECONDS = 0.5


@router.post("/login")
async def login(
    body: LoginIn,
    response: Response,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TokenResponse | MfaPendingOut:
    auth = await container.login(session).execute(body.email, body.password, context)
    response.headers["Cache-Control"] = "no-store"
    if isinstance(auth, PendingMfa):
        clear_session_cookies(response, container.settings)
        return MfaPendingOut.from_pending(auth)
    set_session_cookies(response, auth, container.settings)
    return TokenResponse.from_session(auth)


@router.post("/refresh", dependencies=[Depends(require_csrf)])
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TokenResponse:
    # This invokes the refresh use case, not a SQL cursor; its repository binds values.
    # nosemgrep: python.django.security.injection.sql.sql-injection-using-db-cursor-execute.sql-injection-db-cursor-execute  # noqa: E501
    secret = request.cookies.get(REFRESH_COOKIE)
    auth = await container.refresh(session).execute(secret, context)
    set_session_cookies(response, auth, container.settings)
    return TokenResponse.from_session(auth)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
async def logout(
    request: Request,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    # This invokes the logout use case, not a SQL cursor; its repository binds values.
    # nosemgrep: python.django.security.injection.sql.sql-injection-using-db-cursor-execute.sql-injection-db-cursor-execute  # noqa: E501
    await container.logout(session).execute(request.cookies.get(REFRESH_COOKIE), context)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response, container.settings)
    return response


@router.post("/request-account", status_code=status.HTTP_202_ACCEPTED)
async def request_account(
    body: RequestAccountIn,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MessageOut:
    await container.request_account(session).execute(
        body.email, body.display_name, body.reason, context
    )
    return MessageOut(message=REQUEST_ACCOUNT_MESSAGE)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: ForgotPasswordIn,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MessageOut:
    started = asyncio.get_running_loop().time()
    email = normalise_email(body.email)
    link = await container.forgot_password(session).execute(email, context, send_email=False)
    if link is not None:
        background_tasks.add_task(container.email_sender.send_link, email, TokenPurpose.RESET, link)
    # SMTP cannot affect response timing; both addresses wait to a common floor.
    await asyncio.sleep(
        max(0, FORGOT_RESPONSE_FLOOR_SECONDS - (asyncio.get_running_loop().time() - started))
    )
    return MessageOut(message=FORGOT_MESSAGE)


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    body: SetPasswordIn,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    # SetPasswordUseCase validates the domain password policy before hashing or writing.
    # nosemgrep: python.django.security.audit.unvalidated-password.unvalidated-password
    await container.set_password(session).execute(body.token, body.new_password, context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

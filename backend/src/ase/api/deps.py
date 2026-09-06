"""FastAPI dependencies: container, session, request context, current user, CSRF."""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ase.api.cookies import CSRF_COOKIE, CSRF_HEADER
from ase.api.errors import CsrfFailed
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.policy import require_admin
from ase.container import Container
from ase.domain.errors import Unauthenticated
from ase.domain.users import User

bearer_scheme = HTTPBearer(auto_error=False)
MAX_USER_AGENT = 256


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


async def get_session(container: ContainerDep) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_request_context(request: Request) -> RequestContext:
    # Uvicorn applies forwarded headers only from its configured trusted proxies.
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if user_agent is not None:
        user_agent = user_agent[:MAX_USER_AGENT]
    return RequestContext(ip=ip, user_agent=user_agent)


ContextDep = Annotated[RequestContext, Depends(get_request_context)]


async def get_current_user(
    container: ContainerDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthenticated()
    claims = container.issuer.verify(credentials.credentials)
    # Authentication must release its connection before a streaming response starts.
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        return await validate_current_session(
            claims, repositories.users, repositories.refresh_tokens, container.clock
        )


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_access_claims(
    container: ContainerDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AccessClaims:
    """The verified claims of the presented token, for routes that need its real expiry."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthenticated()
    return container.issuer.verify(credentials.credentials)


ClaimsDep = Annotated[AccessClaims, Depends(get_access_claims)]


def get_admin_user(user: CurrentUser) -> User:
    require_admin(user)
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise CsrfFailed()

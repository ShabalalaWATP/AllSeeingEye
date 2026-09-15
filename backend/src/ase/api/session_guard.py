"""Revalidate the original HTTP session before retaining or releasing protected material."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.policy import require_admin
from ase.domain.errors import Unauthenticated

if TYPE_CHECKING:
    from ase.container import Container


async def validate_request_session(
    container: "Container",
    claims: AccessClaims,
    *,
    admin_only: bool = False,
    session: AsyncSession | None = None,
) -> None:
    async def check(current: AsyncSession) -> None:
        # User reads refresh their identity-map row. A supplied transaction avoids
        # a second SQLite connection rolling back a pending job/edition write.
        repositories = container.repositories(current)
        user = await validate_current_session(
            claims, repositories.users, repositories.refresh_tokens, container.clock
        )
        if admin_only:
            require_admin(user)

    if session is None:
        async with container.session_factory() as fresh:
            await check(fresh)
    else:
        await check(session)
    # The original token can expire while the database reads or close are awaited.
    if claims.expires_at <= container.clock.now():
        raise Unauthenticated("The session has ended. Sign in again.")


def validate_request_expiry(container: "Container", claims: AccessClaims) -> None:
    """No await may reopen a release gap after the guarded private-object checks."""
    if claims.expires_at <= container.clock.now():
        raise Unauthenticated("The session has ended. Sign in again.")

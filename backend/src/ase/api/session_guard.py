"""Revalidate the original HTTP session before retaining or releasing protected material."""

from typing import TYPE_CHECKING

from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.policy import require_admin
from ase.domain.errors import Unauthenticated

if TYPE_CHECKING:
    from ase.container import Container


async def validate_request_session(
    container: "Container", claims: AccessClaims, *, admin_only: bool = False
) -> None:
    # Use fresh committed state rather than the report request's identity map.
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        user = await validate_current_session(
            claims, repositories.users, repositories.refresh_tokens, container.clock
        )
        if admin_only:
            require_admin(user)
    # The original token can expire while the database reads or close are awaited.
    if claims.expires_at <= container.clock.now():
        raise Unauthenticated("The session has ended. Sign in again.")

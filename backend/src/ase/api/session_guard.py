"""Revalidate the original HTTP session immediately before retaining generated material."""

from typing import TYPE_CHECKING

from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.domain.errors import Unauthenticated

if TYPE_CHECKING:
    from ase.container import Container


async def validate_request_session(container: "Container", claims: AccessClaims) -> None:
    # Use fresh committed state rather than the report request's identity map.
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        await validate_current_session(
            claims, repositories.users, repositories.refresh_tokens, container.clock
        )
    # The original token can expire while the database reads or close are awaited.
    if claims.expires_at <= container.clock.now():
        raise Unauthenticated("The session has ended. Sign in again.")

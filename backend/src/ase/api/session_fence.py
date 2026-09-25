"""Release fence: revalidate the presented session before protected material leaves.

Routes take `FenceDep`. After private reads or external work they call `confirm()`,
then `assert_live()` with no await before the protected result is returned or
retained. `release()` performs that whole ending for a finished value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, TypeVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ase.api.deps import ClaimsDep, ContainerDep
from ase.application.auth.current_session import validate_current_session
from ase.application.policy import require_admin
from ase.domain.errors import Unauthenticated

if TYPE_CHECKING:
    from ase.application.dto import AccessClaims
    from ase.container import Container

T = TypeVar("T")


class SessionFence:
    """One request's fence, bound to its container and verified token claims."""

    def __init__(self, container: Container, claims: AccessClaims) -> None:
        self._container = container
        self._claims = claims

    async def confirm(
        self, *, session: AsyncSession | None = None, admin_only: bool = False
    ) -> None:
        """Re-read the user and refresh family; the token must still be unexpired after."""
        if session is None:
            async with self._container.session_factory() as fresh:
                await self._check(fresh, admin_only=admin_only)
        else:
            # A supplied transaction avoids a second SQLite connection rolling back a
            # pending job or edition write, and refreshes the identity-map user row.
            await self._check(session, admin_only=admin_only)
        # The original token can expire while the database reads or close are awaited.
        self.assert_live()

    def assert_live(self) -> None:
        """No await may reopen a release gap after this and before the result leaves."""
        if self._claims.expires_at <= self._container.clock.now():
            raise Unauthenticated("The session has ended. Sign in again.")

    async def release(
        self, value: T, *, session: AsyncSession | None = None, admin_only: bool = False
    ) -> T:
        """Confirm the session, then hand back an already computed protected value."""
        await self.confirm(session=session, admin_only=admin_only)
        return value

    async def _check(self, session: AsyncSession, *, admin_only: bool) -> None:
        repositories = self._container.repositories(session)
        user = await validate_current_session(
            self._claims, repositories.users, repositories.refresh_tokens, self._container.clock
        )
        if admin_only:
            require_admin(user)


def request_fence(container: ContainerDep, claims: ClaimsDep) -> SessionFence:
    return SessionFence(container, claims)


FenceDep = Annotated[SessionFence, Depends(request_fence)]

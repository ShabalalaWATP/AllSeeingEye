"""Exact-handle invitations that never confirm whether a hidden account exists."""

from __future__ import annotations

from uuid import UUID

from ase.application.account.directory_profile import resolve_exact_handle
from ase.application.dto import RequestContext
from ase.application.ports import RateLimiter, UnitOfWork, UserRepository
from ase.application.ports.directory_profile import DirectoryProfileRepository
from ase.application.teams.invitations import TeamInvitationService
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, RateLimited
from ase.domain.users import User

HANDLE_SUBMISSIONS_PER_WINDOW = 20
HANDLE_WINDOW_SECONDS = 3600


class HandleInvitationUseCase:
    """Send a Member invitation to an exact username, returning the same outcome for all handles.

    Sender authority, archive state, note validity and the team's pending limit are
    checked first, because they describe the caller's own team. Every recipient-specific
    outcome (unknown, inactive, already a member, already invited, protected
    Administrator) is then indistinguishable from a successful submission.
    """

    def __init__(
        self,
        invitations: TeamInvitationService,
        profiles: DirectoryProfileRepository,
        users: UserRepository,
        limiter: RateLimiter,
        uow: UnitOfWork,
    ) -> None:
        self._invitations = invitations
        self._profiles = profiles
        self._users = users
        self._limiter = limiter
        self._uow = uow

    async def submit(
        self,
        actor: User,
        team_id: UUID,
        username: str,
        note: str | None,
        context: RequestContext,
    ) -> None:
        await self._invitations.authorise_sender(actor, team_id, note)
        retry_after = self._limiter.hit(
            f"directory-handle-invite:{actor.id}",
            HANDLE_SUBMISSIONS_PER_WINDOW,
            HANDLE_WINDOW_SECONDS,
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        recipient_id = await resolve_exact_handle(self._profiles, self._users, username)
        if recipient_id is None:
            await self._uow.rollback()
            return
        try:
            await self._invitations.send(
                actor, team_id, recipient_id, note, context, require_discoverable=False
            )
        except (Conflict, Forbidden, InvalidRequest, NotFound):
            await self._uow.rollback()

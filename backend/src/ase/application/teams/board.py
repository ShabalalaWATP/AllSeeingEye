"""Authoritative team board reading, posting, editing and read tracking."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import UnitOfWork, UserRepository
from ase.application.ports.services import Clock
from ase.application.ports.team_board import TeamBoardRepository
from ase.application.ports.teams import TeamRepository
from ase.application.teams.board_access import (
    STALE_POST,
    BoardActor,
    board_actor,
    require_revision,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from ase.domain.team_board import (
    MAX_PAGE_SIZE,
    MAX_REPLIES_PER_POST,
    UNREAD_COUNT_CAP,
    TeamBoardPage,
    TeamBoardPost,
    TeamBoardReadCursor,
    clean_text,
)
from ase.domain.users import User


class TeamBoardService:
    def __init__(
        self,
        board: TeamBoardRepository,
        teams: TeamRepository,
        users: UserRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._board = board
        self._teams = teams
        self._users = users
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def _actor(self, actor: User, team_id: UUID, *, write: bool) -> BoardActor:
        return await board_actor(self._users, self._teams, actor, team_id, write=write)

    async def unread_for(self, access: BoardActor) -> int:
        """Unread posts for the caller's current membership; a stale cursor counts as none."""
        cursor = await self._board.get_cursor(access.team.id, access.user.id)
        joined = access.membership.joined_at if access.membership else None
        since = cursor.last_read_at if cursor and cursor.membership_joined_at == joined else None
        return await self._board.unread_count(
            access.team.id, access.user.id, since, UNREAD_COUNT_CAP
        )

    async def list(self, actor: User, team_id: UUID, limit: int, offset: int) -> TeamBoardPage:
        if not 1 <= limit <= MAX_PAGE_SIZE or not 0 <= offset <= 10_000:
            raise InvalidRequest("Invalid board page bounds.")
        access = await self._actor(actor, team_id, write=False)
        page = await self._board.list_posts(team_id, limit, offset)
        return replace(page, unread_count=await self.unread_for(access))

    async def mark_read(self, actor: User, team_id: UUID, last_seen_post_id: UUID) -> int:
        """Advance the caller's cursor to a post they have loaded, then return unread."""
        access = await self._actor(actor, team_id, write=False)
        post = await self._board.get(last_seen_post_id)
        if post is None or post.team_id != team_id:
            raise NotFound()
        joined = access.membership.joined_at if access.membership else None
        existing = await self._board.get_cursor(team_id, access.user.id)
        read_at, read_id = post.created_at, post.id
        if (
            existing is not None
            and existing.membership_joined_at == joined
            and existing.last_read_at >= read_at
        ):
            read_at, read_id = existing.last_read_at, existing.last_read_post_id
        await self._board.put_cursor(
            TeamBoardReadCursor(
                team_id, access.user.id, joined, read_at, read_id, self._clock.now()
            )
        )
        await self._uow.commit()
        return await self.unread_for(access)

    async def create(
        self,
        actor: User,
        team_id: UUID,
        text: str,
        parent_id: UUID | None,
        context: RequestContext,
    ) -> TeamBoardPost:
        access = await self._actor(actor, team_id, write=True)
        try:
            value = clean_text(text, reply=parent_id is not None)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if parent_id is not None:
            parent = await self._board.get(parent_id)
            if parent is None or parent.team_id != team_id or parent.parent_id is not None:
                raise InvalidRequest("Replies must reference a post in this team.")
            if parent.deleted_at is not None:
                raise InvalidRequest("Deleted posts cannot receive replies.")
            if await self._board.reply_count(parent_id) >= MAX_REPLIES_PER_POST:
                raise InvalidRequest(
                    f"A post can receive up to {MAX_REPLIES_PER_POST} replies. Start a new post."
                )
        now = self._clock.now()
        post = TeamBoardPost(uuid4(), team_id, access.user.id, value, now, now, parent_id)
        await self._board.add(post)
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_CREATED,
            actor=access.user.id,
            subject=str(post.id),
            ip=context.ip,
            details={"team_id": str(team_id), "reply": parent_id is not None},
        )
        await self._uow.commit()
        return post

    async def edit(
        self,
        actor: User,
        team_id: UUID,
        post_id: UUID,
        text: str,
        expected_revision: int,
        context: RequestContext,
    ) -> TeamBoardPost:
        post = await self._board.get(post_id)
        if post is None or post.team_id != team_id:
            raise NotFound()
        access = await self._actor(actor, team_id, write=True)
        # Only the author may change the words attributed to them. Moderators can
        # pin or remove a post, but never rewrite it under someone else's name.
        if post.author_id != access.user.id:
            raise Forbidden("Only the author can edit this post.")
        if post.deleted_at is not None:
            raise InvalidRequest("Removed posts cannot be edited.")
        require_revision(post, expected_revision)
        try:
            value = clean_text(text, reply=post.parent_id is not None)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        now = self._clock.now()
        updated = replace(
            post, text=value, updated_at=now, edited_at=now, revision=post.revision + 1
        )
        if not await self._board.save_if_revision(updated, expected_revision):
            await self._uow.rollback()
            raise Conflict(STALE_POST)
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_EDITED,
            actor=access.user.id,
            subject=str(post.id),
            ip=context.ip,
            details={"team_id": str(team_id)},
        )
        await self._uow.commit()
        return updated

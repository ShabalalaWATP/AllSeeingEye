"""Removal and pinning of team board posts, with audited moderation reasons.

Authors may remove their own posts.  Administrators and this team's Managers may
also pin, unpin and remove other people's posts, including an Administrator's,
but must give a reason.  The reason is kept in the audit log only; the public
tombstone says that a moderator removed the post, never why.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

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
    AUTHOR_TOMBSTONE,
    MAX_PINNED_POSTS,
    MODERATOR_TOMBSTONE,
    BoardRemoval,
    TeamBoardPost,
    clean_reason,
)
from ase.domain.users import User


class TeamBoardModerationService:
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

    async def _load(
        self, actor: User, team_id: UUID, post_id: UUID
    ) -> tuple[TeamBoardPost, BoardActor]:
        access = await board_actor(self._users, self._teams, actor, team_id, write=True)
        post = await self._board.get(post_id)
        if post is None or post.team_id != team_id:
            raise NotFound()
        return post, access

    @staticmethod
    def _reason(access: BoardActor, post: TeamBoardPost, reason: str | None) -> str | None:
        if post.author_id == access.user.id:
            return None
        if not access.moderator:
            raise Forbidden()
        try:
            return clean_reason(reason)
        except ValueError as exc:
            raise InvalidRequest(str(exc), fields={"reason": str(exc)}) from exc

    async def _write(self, updated: TeamBoardPost, expected_revision: int) -> None:
        if not await self._board.save_if_revision(updated, expected_revision):
            await self._uow.rollback()
            raise Conflict(STALE_POST)

    async def remove(
        self,
        actor: User,
        team_id: UUID,
        post_id: UUID,
        expected_revision: int,
        reason: str | None,
        context: RequestContext,
    ) -> TeamBoardPost:
        post, access = await self._load(actor, team_id, post_id)
        moderation_reason = self._reason(access, post, reason)
        require_revision(post, expected_revision)
        if post.deleted_at is not None:
            raise Conflict("This post has already been removed.")
        now = self._clock.now()
        moderated = moderation_reason is not None
        updated = replace(
            post,
            text=MODERATOR_TOMBSTONE if moderated else AUTHOR_TOMBSTONE,
            removal=BoardRemoval.MODERATOR if moderated else BoardRemoval.AUTHOR,
            deleted_at=now,
            is_pinned=False,
            updated_at=now,
            revision=post.revision + 1,
        )
        await self._write(updated, expected_revision)
        details: dict[str, object] = {"team_id": str(team_id), "moderation": moderated}
        if moderation_reason is not None:
            details |= {"author_id": str(post.author_id), "reason": moderation_reason}
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_REMOVED,
            actor=access.user.id,
            subject=str(post.id),
            ip=context.ip,
            details=details,
        )
        await self._uow.commit()
        return updated

    async def pin(
        self,
        actor: User,
        team_id: UUID,
        post_id: UUID,
        pinned: bool,
        expected_revision: int,
        reason: str | None,
        context: RequestContext,
    ) -> TeamBoardPost:
        post, access = await self._load(actor, team_id, post_id)
        if not access.moderator:
            raise Forbidden()
        moderation_reason = self._reason(access, post, reason)
        if post.parent_id is not None:
            raise InvalidRequest("Only top-level posts can be pinned.")
        if post.deleted_at is not None:
            raise InvalidRequest("Removed posts cannot be pinned.")
        require_revision(post, expected_revision)
        if pinned == post.is_pinned:
            await self._uow.commit()
            return post
        # The authority check holds the team lock through the write and commit.
        if pinned and await self._board.pinned_count(team_id) >= MAX_PINNED_POSTS:
            await self._uow.rollback()
            raise Conflict(f"A team can pin up to {MAX_PINNED_POSTS} board posts.")
        updated = replace(
            post, is_pinned=pinned, updated_at=self._clock.now(), revision=post.revision + 1
        )
        await self._write(updated, expected_revision)
        details: dict[str, object] = {"team_id": str(team_id), "moderation": False}
        if moderation_reason is not None:
            details |= {
                "moderation": True,
                "author_id": str(post.author_id),
                "reason": moderation_reason,
            }
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_PINNED if pinned else AuditAction.TEAM_BOARD_POST_UNPINNED,
            actor=access.user.id,
            subject=str(post.id),
            ip=context.ip,
            details=details,
        )
        await self._uow.commit()
        return updated

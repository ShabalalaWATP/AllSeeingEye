"""Authoritative team board actions."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import UnitOfWork, UserRepository
from ase.application.ports.services import Clock
from ase.application.ports.team_board import TeamBoardRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.team_board import TeamBoardPage, TeamBoardPost, clean_text
from ase.domain.teams import MembershipRole
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

    async def _actor(self, actor: User, team_id: UUID, *, write: bool) -> tuple[User, bool]:
        current = await self._users.get_by_id(actor.id)
        if (
            current is None
            or not current.is_active
            or current.security_version != actor.security_version
        ):
            raise Unauthenticated()
        team = await self._teams.get(team_id)
        membership = await self._teams.get_membership(team_id, current.id)
        if team is None or (not current.is_admin and membership is None):
            raise NotFound()
        if write and (not team.is_active):
            raise InvalidRequest("Archived teams are read-only.")
        return current, current.is_admin or (
            membership is not None and membership.role is MembershipRole.MANAGER
        )

    async def list(self, actor: User, team_id: UUID, limit: int, offset: int) -> TeamBoardPage:
        if not 1 <= limit <= 20 or not 0 <= offset <= 10_000:
            raise InvalidRequest("Invalid board page bounds.")
        await self._actor(actor, team_id, write=False)
        return await self._board.list_posts(team_id, limit, offset)

    async def create(
        self,
        actor: User,
        team_id: UUID,
        text: str,
        parent_id: UUID | None,
        context: RequestContext,
    ) -> TeamBoardPost:
        current, _ = await self._actor(actor, team_id, write=True)
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
        now = self._clock.now()
        post = TeamBoardPost(uuid4(), team_id, current.id, value, now, now, parent_id)
        await self._board.add(post)
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_CREATED,
            actor=current.id,
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
        current, manager = await self._actor(actor, post.team_id, write=True)
        if post.deleted_at is not None or (post.author_id != current.id and not manager):
            raise Forbidden()
        if expected_revision != post.revision:
            raise InvalidRequest("This post changed. Reload it before saving again.")
        try:
            value = clean_text(text, reply=post.parent_id is not None)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        updated = replace(
            post, text=value, updated_at=self._clock.now(), revision=post.revision + 1
        )
        await self._board.save(updated)
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_EDITED,
            actor=current.id,
            subject=str(post.id),
            ip=context.ip,
            details={"team_id": str(post.team_id)},
        )
        await self._uow.commit()
        return updated

    async def delete(
        self,
        actor: User,
        team_id: UUID,
        post_id: UUID,
        expected_revision: int,
        context: RequestContext,
    ) -> None:
        post = await self._board.get(post_id)
        if post is None or post.team_id != team_id:
            raise NotFound()
        current, manager = await self._actor(actor, post.team_id, write=True)
        if post.deleted_at is not None or (post.author_id != current.id and not manager):
            raise Forbidden()
        if expected_revision != post.revision:
            raise InvalidRequest("This post changed. Reload it before saving again.")
        updated = replace(
            post,
            text="[Removed by author]" if post.author_id == current.id else "[Removed by manager]",
            deleted_at=self._clock.now(),
            is_pinned=False,
            updated_at=self._clock.now(),
            revision=post.revision + 1,
        )
        await self._board.save(updated)
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_REMOVED,
            actor=current.id,
            subject=str(post.id),
            ip=context.ip,
            details={"team_id": str(post.team_id)},
        )
        await self._uow.commit()

    async def pin(
        self,
        actor: User,
        team_id: UUID,
        post_id: UUID,
        pinned: bool,
        expected_revision: int,
        context: RequestContext,
    ) -> TeamBoardPost:
        post = await self._board.get(post_id)
        if post is None or post.team_id != team_id:
            raise NotFound()
        current, manager = await self._actor(actor, post.team_id, write=True)
        if not manager or post.deleted_at is not None:
            raise Forbidden()
        if expected_revision != post.revision:
            raise InvalidRequest("This post changed. Reload it before saving again.")
        if pinned and not post.is_pinned and await self._board.pinned_count(post.team_id) >= 3:
            raise InvalidRequest("A team can pin up to three board posts.")
        updated = replace(
            post, is_pinned=pinned, updated_at=self._clock.now(), revision=post.revision + 1
        )
        await self._board.save(updated)
        await self._auditor.record(
            AuditAction.TEAM_BOARD_POST_PINNED if pinned else AuditAction.TEAM_BOARD_POST_UNPINNED,
            actor=current.id,
            subject=str(post.id),
            ip=context.ip,
            details={"team_id": str(post.team_id)},
        )
        await self._uow.commit()
        return updated

"""Bounded SQL pagination for team board posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.team_board_models import TeamBoardPostRow
from ase.domain.team_board import TeamBoardPage, TeamBoardPost, TeamBoardPostView


def _post(row: TeamBoardPostRow) -> TeamBoardPost:
    return TeamBoardPost(
        row.id,
        row.team_id,
        row.author_id,
        row.text,
        row.created_at,
        row.updated_at,
        row.parent_id,
        row.is_pinned,
        row.deleted_at,
        row.revision,
    )


class SqlTeamBoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_posts(self, team_id: UUID, limit: int, offset: int) -> TeamBoardPage:
        base = (
            select(TeamBoardPostRow, UserRow.display_name)
            .join(UserRow, UserRow.id == TeamBoardPostRow.author_id)
            .where(TeamBoardPostRow.team_id == team_id)
        )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(
                    select(TeamBoardPostRow.id)
                    .where(TeamBoardPostRow.team_id == team_id)
                    .subquery()
                )
            )
            or 0
        )
        rows = await self._session.execute(
            base.order_by(TeamBoardPostRow.created_at.desc(), TeamBoardPostRow.id)
            .offset(offset)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return TeamBoardPage(
            tuple(TeamBoardPostView(_post(row), display_name) for row, display_name in rows),
            total,
            offset,
            limit,
        )

    async def get(self, post_id: UUID) -> TeamBoardPost | None:
        row = await self._session.get(TeamBoardPostRow, post_id, populate_existing=True)
        return _post(row) if row else None

    async def add(self, post: TeamBoardPost) -> None:
        self._session.add(
            TeamBoardPostRow(
                id=post.id,
                team_id=post.team_id,
                author_id=post.author_id,
                text=post.text,
                created_at=post.created_at,
                updated_at=post.updated_at,
                parent_id=post.parent_id,
                is_pinned=post.is_pinned,
                deleted_at=post.deleted_at,
                revision=post.revision,
            )
        )
        await self._session.flush()

    async def save(self, post: TeamBoardPost) -> None:
        row = await self._session.get(TeamBoardPostRow, post.id)
        if row is None:
            raise ValueError("Board post does not exist.")
        row.text = post.text
        row.updated_at = post.updated_at
        row.is_pinned = post.is_pinned
        row.deleted_at = post.deleted_at
        row.revision = post.revision
        await self._session.flush()

    async def pinned_count(self, team_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(TeamBoardPostRow)
                .where(
                    TeamBoardPostRow.team_id == team_id,
                    TeamBoardPostRow.is_pinned.is_(True),
                    TeamBoardPostRow.deleted_at.is_(None),
                )
            )
            or 0
        )

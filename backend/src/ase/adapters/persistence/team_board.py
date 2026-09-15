"""Bounded SQL pagination, conditional writes and read cursors for team board posts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.team_board_models import TeamBoardPostRow, TeamBoardReadCursorRow
from ase.domain.team_board import (
    BoardRemoval,
    TeamBoardPage,
    TeamBoardPost,
    TeamBoardPostView,
    TeamBoardReadCursor,
)


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
        row.edited_at,
        BoardRemoval(row.removal) if row.removal else None,
    )


def _with_author() -> Any:
    return select(TeamBoardPostRow, UserRow.display_name).join(
        UserRow, UserRow.id == TeamBoardPostRow.author_id
    )


class SqlTeamBoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_posts(self, team_id: UUID, limit: int, offset: int) -> TeamBoardPage:
        roots = (TeamBoardPostRow.team_id == team_id, TeamBoardPostRow.parent_id.is_(None))
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(TeamBoardPostRow).where(*roots)
            )
            or 0
        )
        rows = await self._session.execute(
            _with_author()
            .where(*roots)
            .order_by(
                TeamBoardPostRow.is_pinned.desc(),
                TeamBoardPostRow.created_at.desc(),
                TeamBoardPostRow.id,
            )
            .offset(offset)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        items = tuple(TeamBoardPostView(_post(row), name) for row, name in rows)
        replies: tuple[TeamBoardPostView, ...] = ()
        if items:
            # Reply creation is capped per post, so this stays bounded by the page size.
            reply_rows = await self._session.execute(
                _with_author()
                .where(
                    TeamBoardPostRow.team_id == team_id,
                    TeamBoardPostRow.parent_id.in_([item.post.id for item in items]),
                )
                .order_by(TeamBoardPostRow.created_at, TeamBoardPostRow.id)
                .execution_options(populate_existing=True)
            )
            replies = tuple(TeamBoardPostView(_post(row), name) for row, name in reply_rows)
        return TeamBoardPage(items, replies, total, offset, limit)

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
                edited_at=post.edited_at,
                removal=post.removal.value if post.removal else None,
            )
        )
        await self._session.flush()

    async def save_if_revision(self, post: TeamBoardPost, expected_revision: int) -> bool:
        # A conditional UPDATE is atomic on SQLite and PostgreSQL: of two writers
        # holding the same revision, exactly one matches the row.
        result = await self._session.execute(
            update(TeamBoardPostRow)
            .where(
                TeamBoardPostRow.id == post.id,
                TeamBoardPostRow.team_id == post.team_id,
                TeamBoardPostRow.revision == expected_revision,
            )
            .values(
                text=post.text,
                updated_at=post.updated_at,
                is_pinned=post.is_pinned,
                deleted_at=post.deleted_at,
                revision=post.revision,
                edited_at=post.edited_at,
                removal=post.removal.value if post.removal else None,
            )
            .execution_options(synchronize_session=False)
        )
        return int(cast(CursorResult[Any], result).rowcount or 0) == 1

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

    async def pinned(self, team_id: UUID, limit: int) -> list[TeamBoardPostView]:
        rows = await self._session.execute(
            _with_author()
            .where(
                TeamBoardPostRow.team_id == team_id,
                TeamBoardPostRow.is_pinned.is_(True),
                TeamBoardPostRow.deleted_at.is_(None),
            )
            .order_by(TeamBoardPostRow.created_at.desc(), TeamBoardPostRow.id)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [TeamBoardPostView(_post(row), name) for row, name in rows]

    async def reply_count(self, parent_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(TeamBoardPostRow)
                .where(TeamBoardPostRow.parent_id == parent_id)
            )
            or 0
        )

    async def get_cursor(self, team_id: UUID, user_id: UUID) -> TeamBoardReadCursor | None:
        row = await self._session.get(
            TeamBoardReadCursorRow, (team_id, user_id), populate_existing=True
        )
        if row is None:
            return None
        return TeamBoardReadCursor(
            row.team_id,
            row.user_id,
            row.membership_joined_at,
            row.last_read_at,
            row.last_read_post_id,
            row.updated_at,
        )

    async def put_cursor(self, cursor: TeamBoardReadCursor) -> None:
        dialect = self._session.get_bind().dialect.name
        insert = pg_insert if dialect == "postgresql" else sqlite_insert
        values = {
            "membership_joined_at": cursor.membership_joined_at,
            "last_read_at": cursor.last_read_at,
            "last_read_post_id": cursor.last_read_post_id,
            "updated_at": cursor.updated_at,
        }
        await self._session.execute(
            insert(TeamBoardReadCursorRow)
            .values(team_id=cursor.team_id, user_id=cursor.user_id, **values)
            .on_conflict_do_update(index_elements=["team_id", "user_id"], set_=values)
        )

    async def unread_count(
        self, team_id: UUID, user_id: UUID, since: datetime | None, cap: int
    ) -> int:
        conditions = [
            TeamBoardPostRow.team_id == team_id,
            TeamBoardPostRow.author_id != user_id,
            TeamBoardPostRow.deleted_at.is_(None),
        ]
        if since is not None:
            conditions.append(TeamBoardPostRow.created_at > since)
        bounded = select(TeamBoardPostRow.id).where(*conditions).limit(cap).subquery()
        return int(await self._session.scalar(select(func.count()).select_from(bounded)) or 0)

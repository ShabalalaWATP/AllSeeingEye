"""SQL for board mention recipients, filtered by current access before limits and counts."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.team_board_models import TeamBoardMentionRow, TeamBoardPostRow
from ase.adapters.persistence.teams import TeamMembershipRow, TeamRow
from ase.domain.board_mentions import MentionNotice, snippet

Mention = TeamBoardMentionRow
Post = TeamBoardPostRow


def _readable(user_id: UUID) -> Any:
    """Mentions of ``user_id`` on live posts in active teams, within their current membership."""
    return (
        select(Mention, Post.parent_id, Post.text, TeamRow.name, UserRow.display_name)
        .join(Post, and_(Post.id == Mention.post_id, Post.team_id == Mention.team_id))
        .join(TeamRow, TeamRow.id == Mention.team_id)
        .join(
            TeamMembershipRow,
            and_(
                TeamMembershipRow.team_id == Mention.team_id,
                TeamMembershipRow.user_id == Mention.recipient_id,
                # A mention belongs to the membership it was made in; rejoining starts afresh.
                TeamMembershipRow.joined_at <= Mention.created_at,
            ),
        )
        .join(UserRow, UserRow.id == Post.author_id)
        .where(
            Mention.recipient_id == user_id,
            Post.deleted_at.is_(None),
            TeamRow.is_active.is_(True),
        )
    )


def _notice(row: Any) -> MentionNotice:
    mention, parent_id, text, team_name, author_name = row
    return MentionNotice(
        post_id=mention.post_id,
        thread_id=parent_id or mention.post_id,
        team_id=mention.team_id,
        team_name=team_name,
        author_name=author_name,
        snippet=snippet(text),
        created_at=mention.created_at,
        read_at=mention.read_at,
    )


class SqlBoardMentionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_post(self, post_id: UUID) -> dict[str, UUID]:
        rows = await self._session.execute(
            select(Mention.handle, Mention.recipient_id).where(Mention.post_id == post_id)
        )
        return dict(rows.tuples().all())

    async def add(
        self, post_id: UUID, team_id: UUID, mentions: Mapping[str, UUID], now: datetime
    ) -> None:
        self._session.add_all(
            Mention(
                post_id=post_id,
                recipient_id=recipient,
                team_id=team_id,
                handle=handle,
                created_at=now,
                read_at=None,
            )
            for handle, recipient in mentions.items()
        )
        await self._session.flush()

    async def remove(self, post_id: UUID, handles: Collection[str]) -> None:
        if handles:
            await self._session.execute(
                delete(Mention).where(Mention.post_id == post_id, Mention.handle.in_(handles))
            )

    async def clear(self, post_id: UUID) -> frozenset[UUID]:
        recipients = frozenset((await self.for_post(post_id)).values())
        await self._session.execute(delete(Mention).where(Mention.post_id == post_id))
        return recipients

    async def notices(
        self, user_id: UUID, limit: int, unread_cap: int
    ) -> tuple[list[MentionNotice], int]:
        unread = _readable(user_id).where(Mention.read_at.is_(None))
        capped = unread.with_only_columns(Mention.post_id).limit(unread_cap).subquery()
        total = await self._session.scalar(select(func.count()).select_from(capped))
        rows = await self._session.execute(
            unread.order_by(Mention.created_at.desc(), Mention.post_id).limit(limit)
        )
        return [_notice(row) for row in rows], int(total or 0)

    async def notice(self, user_id: UUID, post_id: UUID) -> MentionNotice | None:
        row = (
            await self._session.execute(_readable(user_id).where(Mention.post_id == post_id))
        ).first()
        return None if row is None else _notice(row)

    async def mark_read(self, user_id: UUID, post_ids: Collection[UUID], now: datetime) -> None:
        if post_ids:
            await self._session.execute(
                update(Mention)
                .where(
                    Mention.recipient_id == user_id,
                    Mention.post_id.in_(tuple(post_ids)),
                    Mention.read_at.is_(None),
                )
                .values(read_at=now)
            )

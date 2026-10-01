"""Persistence boundary for board mention recipients and the notices they read."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.board_mentions import MentionNotice


class BoardMentionRepository(Protocol):
    async def for_post(self, post_id: UUID) -> dict[str, UUID]:
        """The post's stored mentions as handle-as-written to recipient id."""
        ...

    async def add(
        self, post_id: UUID, team_id: UUID, mentions: Mapping[str, UUID], now: datetime
    ) -> None: ...

    async def remove(self, post_id: UUID, handles: Collection[str]) -> None: ...

    async def clear(self, post_id: UUID) -> frozenset[UUID]:
        """Remove every mention of the post and return the recipients."""
        ...

    async def notices(
        self, user_id: UUID, limit: int, unread_cap: int
    ) -> tuple[list[MentionNotice], int]:
        """Unread notices the recipient may read now, newest first, and their capped count.

        Readable means the post is live, the team is active and the recipient's current
        membership began no later than the mention; all of it is filtered in SQL.
        """
        ...

    async def notice(self, user_id: UUID, post_id: UUID) -> MentionNotice | None:
        """One notice under the same current-access rules, read or unread."""
        ...

    async def mark_read(self, user_id: UUID, post_ids: Collection[UUID], now: datetime) -> None:
        """Mark only the caller's own notices read; other recipients are untouched."""
        ...

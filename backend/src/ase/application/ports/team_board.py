"""Persistence boundary for the plain-text team board."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.team_board import (
    TeamBoardPage,
    TeamBoardPost,
    TeamBoardPostView,
    TeamBoardReadCursor,
)


class TeamBoardRepository(Protocol):
    async def list_posts(self, team_id: UUID, limit: int, offset: int) -> TeamBoardPage:
        """Top-level posts, pinned first, with the replies to those posts."""
        ...

    async def get(self, post_id: UUID) -> TeamBoardPost | None: ...

    async def add(self, post: TeamBoardPost) -> None: ...

    async def save_if_revision(self, post: TeamBoardPost, expected_revision: int) -> bool:
        """Write the post only when the stored revision still matches; False otherwise."""
        ...

    async def pinned_count(self, team_id: UUID) -> int: ...

    async def pinned(self, team_id: UUID, limit: int) -> list[TeamBoardPostView]: ...

    async def reply_count(self, parent_id: UUID) -> int: ...

    async def get_cursor(self, team_id: UUID, user_id: UUID) -> TeamBoardReadCursor | None: ...

    async def put_cursor(self, cursor: TeamBoardReadCursor) -> None:
        """Insert or replace the caller's cursor for this team."""
        ...

    async def unread_count(
        self, team_id: UUID, user_id: UUID, since: datetime | None, cap: int
    ) -> int:
        """Visible posts by other people after ``since``, counted up to ``cap``."""
        ...

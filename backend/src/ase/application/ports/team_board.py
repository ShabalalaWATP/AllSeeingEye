"""Persistence boundary for the plain-text team board."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.team_board import TeamBoardPage, TeamBoardPost


class TeamBoardRepository(Protocol):
    async def list_posts(self, team_id: UUID, limit: int, offset: int) -> TeamBoardPage: ...

    async def get(self, post_id: UUID) -> TeamBoardPost | None: ...

    async def add(self, post: TeamBoardPost) -> None: ...

    async def save(self, post: TeamBoardPost) -> None: ...

    async def pinned_count(self, team_id: UUID) -> int: ...

"""Persistence boundary for public directory profiles."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.directory_profile import DirectoryPage, DirectoryProfile


class DirectoryProfileRepository(Protocol):
    async def get(self, user_id: UUID) -> DirectoryProfile | None: ...

    async def save(self, profile: DirectoryProfile) -> None: ...

    async def search(self, query: str, limit: int, offset: int) -> DirectoryPage: ...

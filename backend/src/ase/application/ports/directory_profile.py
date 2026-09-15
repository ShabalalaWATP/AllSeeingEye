"""Persistence and image-processing boundaries for directory profiles."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.directory_avatar import DirectoryAvatar, ProcessedAvatar
from ase.domain.directory_profile import DirectoryPage, DirectoryProfile


class DirectoryProfileRepository(Protocol):
    async def get(self, user_id: UUID) -> DirectoryProfile | None: ...

    async def get_by_username(self, username: str) -> DirectoryProfile | None: ...

    async def save(self, profile: DirectoryProfile) -> None: ...

    async def search(self, query: str, limit: int, offset: int) -> DirectoryPage: ...

    async def get_avatar(self, user_id: UUID) -> DirectoryAvatar | None: ...

    async def save_avatar(self, avatar: DirectoryAvatar) -> None: ...

    async def delete_avatar(self, user_id: UUID) -> None: ...

    async def shares_team(self, viewer_id: UUID, target_id: UUID) -> bool:
        """Whether both accounts currently hold a membership in at least one team."""
        ...


class AvatarProcessor(Protocol):
    async def process(self, data: bytes) -> ProcessedAvatar:
        """Decode, strip metadata and re-encode, raising ``InvalidRequest`` on rejection."""
        ...

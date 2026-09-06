"""Persistence boundary for private account preferences."""

from typing import Protocol
from uuid import UUID

from ase.domain.profile import PersonalProfile


class ProfileRepository(Protocol):
    async def get(self, user_id: UUID, display_name: str) -> PersonalProfile: ...
    async def save(self, user_id: UUID, profile: PersonalProfile) -> None: ...

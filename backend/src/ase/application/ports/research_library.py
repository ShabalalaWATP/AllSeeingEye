"""Library lists and counts must intersect parent visibility before pagination."""

from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.research_library import LibraryPage, LibraryPreference


class ResearchLibraryRepository(Protocol):
    async def get(self, user_id: UUID, report_id: UUID) -> LibraryPreference: ...
    async def save(self, user_id: UUID, report_id: UUID, value: LibraryPreference) -> None: ...
    async def remove(self, user_id: UUID, report_id: UUID) -> None: ...
    async def list_visible(
        self,
        visibility: Visibility,
        limit: int,
        offset: int,
        favourite_only: bool,
        tag: str | None,
    ) -> LibraryPage: ...

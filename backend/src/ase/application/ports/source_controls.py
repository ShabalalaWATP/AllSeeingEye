"""Persisted admission controls for configured public sources."""

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID


class SourceControlRepository(Protocol):
    async def all(self) -> dict[str, bool]: ...
    async def set(self, source_id: str, enabled: bool, at: datetime, actor: UUID) -> None: ...


class SourceAdmission(Protocol):
    def guard(self) -> AbstractAsyncContextManager[None]:
        """Serialise activation commits with final admission/release; never hold across fetches."""
        ...

    async def enabled(self, source_id: str) -> bool: ...
    async def enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]: ...

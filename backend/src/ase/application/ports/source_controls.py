"""Persisted admission controls for configured public sources."""

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID


class SourceControlRepository(Protocol):
    async def all(self) -> dict[str, bool]: ...
    async def set(self, source_id: str, enabled: bool, at: datetime, actor: UUID) -> None: ...


class SourceAdmission(Protocol):
    @property
    def generation(self) -> int:
        """Process-local source-change generation, including changes back to prior values."""
        ...

    def guard(self) -> AbstractAsyncContextManager[None]:
        """Serialise activation commits with final admission/release; never hold across fetches."""
        ...

    async def enabled(self, source_id: str) -> bool: ...
    async def enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]: ...


@runtime_checkable
class LicenceAwareSourceAdmission(Protocol):
    def licence_denial(self, source_id: str) -> str | None:
        """Fixed public reason for an immutable licence veto, or None."""
        ...


@runtime_checkable
class SourceControlAdmission(Protocol):
    async def controls_enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]:
        """Operator switches only, for logical controls rather than fetched source IDs."""
        ...

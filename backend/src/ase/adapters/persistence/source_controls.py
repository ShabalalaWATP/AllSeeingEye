"""Database admission checks shared by live feeds and private research.

Administrator overrides are read into a small in-process snapshot. Any committed
source-control write advances a version that invalidates it (see
source_control_changes), so a disable that commits under the release guard is
observed by the next final admission read. A time-to-live bounds staleness for
writes made outside this process.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.source_control_changes import source_control_version
from ase.adapters.persistence.source_control_models import SourceControlRow
from ase.domain.source_controls import source_control_keys

OVERRIDE_TTL_SECONDS = 30.0


class SqlSourceControlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def all(self) -> dict[str, bool]:
        rows = await self._session.scalars(select(SourceControlRow))
        return {row.source_id: row.enabled for row in rows}

    async def set(self, source_id: str, enabled: bool, at: datetime, actor: UUID) -> None:
        row = await self._session.get(SourceControlRow, source_id)
        if row is None:
            self._session.add(
                SourceControlRow(
                    source_id=source_id,
                    enabled=enabled,
                    updated_at=at,
                    updated_by=actor,
                )
            )
        else:
            row.enabled, row.updated_at, row.updated_by = enabled, at, actor
        await self._session.flush()


@dataclass(frozen=True, slots=True)
class _Overrides:
    version: int
    loaded_at: float
    disabled: frozenset[str]


class SqlSourceAdmission:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        disabled: tuple[str, ...] = (),
        *,
        ttl_seconds: float = OVERRIDE_TTL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sessions = sessions
        self._disabled = frozenset(disabled)
        self._release_lock = asyncio.Lock()
        self._load_lock = asyncio.Lock()
        self._ttl = ttl_seconds
        self._monotonic = monotonic
        self._overrides: _Overrides | None = None

    @property
    def generation(self) -> int:
        return source_control_version()

    @asynccontextmanager
    async def guard(self) -> AsyncIterator[None]:
        """The configured deployment is one API process; share this instance across consumers."""
        async with self._release_lock:
            yield

    async def enabled(self, source_id: str) -> bool:
        blocked = self._disabled | await self._administrator_disabled()
        return not any(key in blocked for key in source_control_keys(source_id))

    async def enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]:
        blocked = self._disabled | await self._administrator_disabled()
        return {
            source_id: not any(key in blocked for key in source_control_keys(source_id))
            for source_id in source_ids
        }

    def _cached(self) -> frozenset[str] | None:
        cached = self._overrides
        if (
            cached is None
            or cached.version != source_control_version()
            or self._monotonic() - cached.loaded_at >= self._ttl
        ):
            return None
        return cached.disabled

    async def _administrator_disabled(self) -> frozenset[str]:
        cached = self._cached()
        if cached is not None:
            return cached
        # One reload serves every waiting caller, so a burst of polls costs one query.
        async with self._load_lock:
            cached = self._cached()
            if cached is not None:
                return cached
            # Stamp with the version seen before the query: a write that commits
            # while it runs advances the version and so invalidates this snapshot.
            version, loaded_at = source_control_version(), self._monotonic()
            async with self._sessions() as session:
                disabled = frozenset(
                    await session.scalars(
                        select(SourceControlRow.source_id).where(
                            SourceControlRow.enabled.is_(False)
                        )
                    )
                )
            self._overrides = _Overrides(version, loaded_at, disabled)
            return disabled

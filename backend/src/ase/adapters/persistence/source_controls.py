"""Fresh database admission checks shared by live feeds and private research."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.source_control_models import SourceControlRow
from ase.domain.source_controls import source_control_keys


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


class SqlSourceAdmission:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], disabled: tuple[str, ...] = ()
    ) -> None:
        self._sessions = sessions
        self._disabled = frozenset(disabled)
        self._release_lock = asyncio.Lock()

    @asynccontextmanager
    async def guard(self) -> AsyncIterator[None]:
        """The configured deployment is one API process; share this instance across consumers."""
        async with self._release_lock:
            yield

    async def enabled(self, source_id: str) -> bool:
        keys = source_control_keys(source_id)
        if any(key in self._disabled for key in keys):
            return False
        async with self._sessions() as session:
            disabled = await session.scalar(
                select(SourceControlRow.source_id)
                .where(
                    SourceControlRow.source_id.in_(keys),
                    SourceControlRow.enabled.is_(False),
                )
                .limit(1)
            )
            return disabled is None

    async def enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]:
        keys = {key for source_id in source_ids for key in source_control_keys(source_id)}
        async with self._sessions() as session:
            overrides = set(
                await session.scalars(
                    select(SourceControlRow.source_id).where(
                        SourceControlRow.source_id.in_(keys),
                        SourceControlRow.enabled.is_(False),
                    )
                )
            )
        blocked = overrides | self._disabled
        return {
            source_id: not any(key in blocked for key in source_control_keys(source_id))
            for source_id in source_ids
        }

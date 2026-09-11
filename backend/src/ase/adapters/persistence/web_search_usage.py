"""Commit bounded provider usage independently of an eventual report/cancellation."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.llm import SqlLlmUsageRepository
from ase.domain.llm import LlmUsage


class SqlWebSearchUsage:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, usage: LlmUsage) -> None:
        # No question, source content, credentials or session identifiers are stored here.
        async with self._sessions() as session:
            await SqlLlmUsageRepository(session).add(usage)
            await session.commit()

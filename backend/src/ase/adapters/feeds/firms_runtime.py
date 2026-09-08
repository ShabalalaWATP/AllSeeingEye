"""Stable FIRMS registration resolves each poll and guards release against credential changes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.feeds.firms import SPEC, FirmsConnector, validate_area
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.ports import Clock
from ase.application.ports.feed_release import FeedUnavailable, FetchedBatch
from ase.application.ports.llm import SecretCipher
from ase.domain.events import Event


class FirmsConnectionProbe:
    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock

    async def test(self, key: str, area: str) -> int:
        return len(await FirmsConnector(self.http, self.clock, key, area).fetch())


class ManagedFirmsConnector:
    spec = SPEC

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        http: FeedHttpClient,
        clock: Clock,
        cipher: SecretCipher,
        *,
        environment_key: str | None,
        area: str,
        disabled: bool,
    ) -> None:
        self.sessions, self.http, self.clock, self.cipher = sessions, http, clock, cipher
        self._environment_key = environment_key
        self.area, self.disabled = validate_area(area), disabled

    async def current_generation(self) -> int:
        if self._environment_key:
            return -1
        async with self.sessions() as session:
            return (await SqlFirmsCredentials(session).get()).active_revision

    async def fetch_batch(self) -> FetchedBatch:
        if self.disabled:
            raise FeedUnavailable("FIRMS is disabled by the operator environment.")
        if self._environment_key:
            key, generation = self._environment_key, -1
        else:
            async with self.sessions() as session:
                row = await SqlFirmsCredentials(session).get()
            if not row.active_encrypted:
                raise FeedUnavailable("FIRMS needs an administrator connection.")
            try:
                key = self.cipher.decrypt(row.active_encrypted)
            except Exception:
                raise FeedFetchError("The stored FIRMS connection cannot be read.") from None
            generation = row.active_revision
        try:
            events = await FirmsConnector(self.http, self.clock, key, self.area).fetch()
        except Exception:
            raise FeedFetchError(
                "FIRMS could not be fetched. Check its connection and area."
            ) from None
        return FetchedBatch(events, generation)

    async def fetch(self) -> list[Event]:
        return (await self.fetch_batch()).events

    @asynccontextmanager
    async def release_guard(self, generation: int) -> AsyncIterator[bool]:
        # Scheduler holds source admission first. Administrative mutations share this
        # database lock, including across processes; retain it through publication.
        async with self.sessions() as session:
            await SqlUserRepository(session).lock_administration()
            row = await SqlFirmsCredentials(session).get()
            enabled = (await SqlSourceControlRepository(session).all()).get(SPEC.id, True)
            valid = (
                enabled
                and not self.disabled
                and (
                    generation == -1
                    if self._environment_key
                    else bool(row.active_encrypted) and generation == row.active_revision
                )
            )
            yield valid
            await session.commit()

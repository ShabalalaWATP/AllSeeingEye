"""Stable FIRMS registration resolves each poll and guards release against credential changes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.feeds.firms import SPEC, FirmsConnector, sensor_spec, validate_area
from ase.adapters.feeds.firms_sensors import NOAA20, FirmsSensor, require_sensor
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
        sensor: FirmsSensor = NOAA20,
    ) -> None:
        self.sessions, self.http, self.clock, self.cipher = sessions, http, clock, cipher
        self._environment_key = environment_key
        self.sensor = require_sensor(sensor)
        self.spec = sensor_spec(sensor)
        self.area, self.disabled = validate_area(area), disabled

    async def current_generation(self) -> int:
        if self._environment_key:
            return -1
        async with self.sessions() as session:
            return (await SqlFirmsCredentials(session).get()).active_revision

    async def fetch_batch(self) -> FetchedBatch:
        if self.disabled:
            raise FeedUnavailable("FIRMS is disabled by the operator environment.")
        async with self.sessions() as session:
            controls = await SqlSourceControlRepository(session).all()
            if not controls.get(SPEC.id, True) or not controls.get(self.spec.id, True):
                raise FeedUnavailable("FIRMS is disabled by an administrator.")
            row = None if self._environment_key else await SqlFirmsCredentials(session).get()
        if self._environment_key:
            key, generation = self._environment_key, -1
        else:
            if row is None or not row.active_encrypted:
                raise FeedUnavailable("FIRMS needs an administrator connection.")
            try:
                key = self.cipher.decrypt(row.active_encrypted)
            except Exception:
                raise FeedFetchError("The stored FIRMS connection cannot be read.") from None
            generation = row.active_revision
        try:
            events = await FirmsConnector(
                self.http, self.clock, key, self.area, sensor=self.sensor
            ).fetch()
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
            row = None if self._environment_key else await SqlFirmsCredentials(session).get()
            controls = await SqlSourceControlRepository(session).all()
            enabled = controls.get(SPEC.id, True) and controls.get(self.spec.id, True)
            valid = (
                enabled
                and not self.disabled
                and (
                    generation == -1
                    if self._environment_key
                    else row is not None
                    and bool(row.active_encrypted)
                    and generation == row.active_revision
                )
            )
            yield valid
            await session.commit()

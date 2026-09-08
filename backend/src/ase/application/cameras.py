"""Shared bounded facility cache with independent source failures and request coalescing."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from ase.application.ports.cameras import CameraSource
from ase.application.ports.services import Clock
from ase.domain.cameras import Camera, CameraCatalogue, CameraProviderStatus
from ase.domain.errors import Unauthenticated
from ase.domain.users import User

MAX_CAMERAS_PER_PROVIDER = 5000
CACHE_TTL = timedelta(minutes=15)
FAILURE_RETRY = timedelta(minutes=1)
MAX_STALE = timedelta(hours=24)


@dataclass
class _CachedSource:
    source: CameraSource
    cameras: tuple[Camera, ...] = ()
    fetched_at: datetime | None = None
    retry_at: datetime | None = None
    failed: bool = False
    warning: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class CameraCatalogueService:
    def __init__(self, sources: tuple[CameraSource, ...], clock: Clock) -> None:
        self._sources = tuple(_CachedSource(source) for source in sources)
        self._clock = clock
        self._limit = asyncio.Semaphore(4)

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(source.source.id for source in self._sources)

    async def initial_catalogue(self, actor: User) -> CameraCatalogue:
        keys = [key for key in ("tfl", "hongkong", "fintraffic") if key in self.provider_ids]
        results = await asyncio.gather(*(self.catalogue(actor, key) for key in keys))
        final = await self.catalogue(actor, keys[-1]) if keys else None
        return CameraCatalogue(
            tuple(c for result in results for c in result.cameras),
            final.providers if final else (),
            self._clock.now(),
        )

    async def catalogue(
        self,
        actor: User,
        provider: str | None = None,
    ) -> CameraCatalogue:
        if not actor.is_active:
            raise Unauthenticated()
        if provider is not None and provider not in {s.source.id for s in self._sources}:
            raise ValueError("Unknown camera provider")
        requested = tuple(s for s in self._sources if provider is None or s.source.id == provider)
        await asyncio.gather(*(self._refresh(s) for s in requested))
        now = self._clock.now()
        statuses = []
        cameras: list[Camera] = []
        for cached in self._sources:
            available = cached.cameras
            if cached.fetched_at is not None and now - cached.fetched_at > MAX_STALE:
                available = ()
            status: Literal["available", "stale", "unavailable", "not_loaded"] = (
                "stale"
                if cached.failed and available
                else "unavailable"
                if cached.failed
                else "not_loaded"
                if cached.fetched_at is None
                else "available"
            )
            statuses.append(
                CameraProviderStatus(
                    cached.source.id,
                    cached.source.name,
                    status,
                    len(available),
                    cached.fetched_at,
                    "Catalogue temporarily unavailable or provider access restricted."
                    if cached.failed
                    else cached.warning,
                )
            )
            if cached in requested:
                cameras.extend(available)
        return CameraCatalogue(tuple(cameras), tuple(statuses), now)

    async def _refresh(self, cached: _CachedSource) -> None:
        async with cached.lock:
            await self._refresh_locked(cached)

    async def _refresh_locked(self, cached: _CachedSource) -> None:
        now = self._clock.now()
        if cached.retry_at is not None and now < cached.retry_at:
            return
        try:
            async with self._limit, asyncio.timeout(45):
                result = await cached.source.fetch()
            if not result:
                raise ValueError("Empty catalogue")
            cached.cameras = result[:MAX_CAMERAS_PER_PROVIDER]
            cached.fetched_at = self._clock.now()
            cached.failed = False
            message = getattr(cached.source, "warning", None)
            cached.warning = message if isinstance(message, str) else None
            cached.retry_at = self._clock.now() + (FAILURE_RETRY if cached.warning else CACHE_TTL)
        except (OSError, ValueError, TimeoutError):
            cached.failed = True
            cached.retry_at = self._clock.now() + FAILURE_RETRY

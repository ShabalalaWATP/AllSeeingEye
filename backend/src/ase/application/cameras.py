"""Shared bounded facility cache with independent source failures and request coalescing."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from ase.application.ports.cameras import CameraSource
from ase.application.ports.services import Clock
from ase.domain.cameras import Camera, CameraCatalogue, CameraProviderStatus
from ase.domain.errors import Unauthenticated
from ase.domain.users import User

MAX_CAMERAS_PER_PROVIDER = 1500
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


class CameraCatalogueService:
    def __init__(self, sources: tuple[CameraSource, ...], clock: Clock) -> None:
        self._sources = tuple(_CachedSource(source) for source in sources)
        self._clock = clock
        self._lock = asyncio.Lock()

    async def catalogue(self, actor: User) -> CameraCatalogue:
        if not actor.is_active:
            raise Unauthenticated()
        async with self._lock:
            await asyncio.gather(*(self._refresh(source) for source in self._sources))
            now = self._clock.now()
            statuses = []
            cameras: list[Camera] = []
            for cached in self._sources:
                if cached.fetched_at is not None and now - cached.fetched_at > MAX_STALE:
                    cached.cameras = ()
                status: Literal["available", "stale", "unavailable"] = (
                    "stale"
                    if cached.failed and cached.cameras
                    else "unavailable"
                    if cached.failed
                    else "available"
                )
                statuses.append(
                    CameraProviderStatus(
                        cached.source.id,
                        cached.source.name,
                        status,
                        len(cached.cameras),
                        cached.fetched_at,
                        "Catalogue temporarily unavailable." if cached.failed else None,
                    )
                )
                cameras.extend(cached.cameras)
            return CameraCatalogue(tuple(cameras), tuple(statuses), now)

    async def _refresh(self, cached: _CachedSource) -> None:
        now = self._clock.now()
        if cached.retry_at is not None and now < cached.retry_at:
            return
        try:
            async with asyncio.timeout(15):
                result = await cached.source.fetch()
            if not result:
                raise ValueError("Empty catalogue")
            cached.cameras = result[:MAX_CAMERAS_PER_PROVIDER]
            cached.fetched_at = self._clock.now()
            cached.failed = False
            cached.retry_at = self._clock.now() + CACHE_TTL
        except (OSError, ValueError, TimeoutError):
            cached.failed = True
            cached.retry_at = self._clock.now() + FAILURE_RETRY

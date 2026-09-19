"""Shared bounded facility cache with independent source failures and request coalescing."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from ase.application.ports.cameras import CameraSource
from ase.application.ports.services import Clock
from ase.domain.cameras import Camera, CameraCatalogue, CameraProviderStatus
from ase.domain.errors import RateLimited, Unauthenticated
from ase.domain.events import BoundingBox, Point
from ase.domain.users import User

MAX_CAMERAS_PER_PROVIDER = 5000
CACHE_TTL = timedelta(minutes=15)
FAILURE_RETRY = timedelta(minutes=1)
MAX_STALE = timedelta(hours=24)
FRAME_TIMEOUT_SECONDS = 20


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
        self._frame_lock = asyncio.Lock()
        self._frame_tasks: dict[tuple[str, str], asyncio.Task[bytes | None]] = {}
        self._frame_waiters = 0
        self._frame_waiters_by_user: dict[str, int] = {}
        self._frame_work_by_user: dict[str, int] = {}
        self._frame_work = 0

    @property
    def sources(self) -> tuple[CameraSource, ...]:
        """Registered providers in registry order, for descriptive inventories."""
        return tuple(cached.source for cached in self._sources)

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(source.source.id for source in self._sources)

    def snapshot(
        self,
        actor: User,
        *,
        bbox: BoundingBox | None = None,
        selected_id: str | None = None,
        limit: int = 100,
    ) -> CameraCatalogue:
        """Read only already-cached metadata, without refreshing any provider or imagery."""
        if not actor.is_active:
            raise Unauthenticated()
        if not 1 <= limit <= 100:
            raise ValueError("Cached camera queries are limited to 100 facilities.")
        now = self._clock.now()
        statuses: list[CameraProviderStatus] = []
        groups = []
        for cached in self._sources:
            fresh_enough = cached.fetched_at is not None and now - cached.fetched_at <= MAX_STALE
            available = cached.cameras if fresh_enough else ()
            status: Literal["available", "stale", "unavailable", "not_loaded"] = (
                "stale"
                if cached.failed and available
                else "available"
                if available
                else "not_loaded"
                if cached.fetched_at is None
                else "unavailable"
            )
            statuses.append(
                CameraProviderStatus(
                    cached.source.id,
                    cached.source.name,
                    status,
                    len(available),
                    cached.fetched_at,
                )
            )
            groups.append(
                iter(
                    camera
                    for camera in available
                    if (selected_id is None or camera.id == selected_id)
                    and (bbox is None or bbox.contains(Point(camera.longitude, camera.latitude)))
                )
            )
        # Round-robin providers so a large first catalogue cannot occupy the entire sample.
        cameras: list[Camera] = []
        while groups and len(cameras) < limit:
            active = []
            for group in groups:
                camera = next(group, None)
                if camera is not None:
                    cameras.append(camera)
                    active.append(group)
                if len(cameras) >= limit:
                    break
            groups = active
        return CameraCatalogue(tuple(cameras), tuple(statuses), now)

    async def frame(self, actor: User, provider: str, frame_id: str) -> bytes | None:
        """One relayed frame from a source that declares frames; other sources answer None."""
        if not actor.is_active:
            raise Unauthenticated()
        for cached in self._sources:
            if cached.source.id != provider:
                continue
            reader = getattr(cached.source, "frame", None)
            if reader is None:
                return None
            key = (provider, frame_id)
            actor_key = str(actor.id)
            async with self._frame_lock:
                actor_waiters = self._frame_waiters_by_user.get(actor_key, 0)
                if self._frame_waiters >= 8 or actor_waiters >= 2:
                    raise RateLimited(1)
                task = self._frame_tasks.get(key)
                if task is None:
                    if self._frame_work >= 2 or self._frame_work_by_user.get(actor_key, 0) >= 1:
                        raise RateLimited(1)
                    self._frame_work += 1
                    self._frame_work_by_user[actor_key] = 1
                    task = asyncio.create_task(
                        self._frame_work_item(key, actor_key, reader, frame_id)
                    )
                    self._frame_tasks[key] = task
                self._frame_waiters += 1
                self._frame_waiters_by_user[actor_key] = actor_waiters + 1
            try:
                data = await asyncio.shield(task)
                return data if isinstance(data, bytes) and data else None
            finally:
                async with self._frame_lock:
                    self._frame_waiters -= 1
                    waiting = self._frame_waiters_by_user[actor_key] - 1
                    if waiting:
                        self._frame_waiters_by_user[actor_key] = waiting
                    else:
                        self._frame_waiters_by_user.pop(actor_key, None)
        raise ValueError("Unknown camera provider")

    async def _frame_work_item(
        self,
        key: tuple[str, str],
        actor_key: str,
        reader: Callable[[str], Awaitable[bytes | None]],
        frame_id: str,
    ) -> bytes | None:
        try:
            async with asyncio.timeout(FRAME_TIMEOUT_SECONDS):
                result = await reader(frame_id)
            return result if isinstance(result, bytes) and result else None
        finally:
            async with self._frame_lock:
                self._frame_tasks.pop(key, None)
                self._frame_work -= 1
                self._frame_work_by_user.pop(actor_key, None)

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

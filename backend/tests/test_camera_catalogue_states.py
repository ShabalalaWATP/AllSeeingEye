"""Camera cache state and initial catalogue call-count regressions."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, call, patch

import pytest

from ase.application.cameras import CameraCatalogueService
from ase.domain.cameras import Camera
from ase.domain.users import User
from helpers import FakeClock


def source(provider: str = "tfl") -> AsyncMock:
    camera = Camera(
        f"{provider}:001",
        provider,
        "Road",
        51.5,
        -0.1,
        "https://example.test/camera.jpg",
        "https://example.test",
        "Source",
    )
    result = AsyncMock(id=provider, fetch=AsyncMock(return_value=(camera,)))
    result.name = "Source"
    return result


async def test_initial_catalogue_reads_each_provider_once(user: User, clock: FakeClock) -> None:
    keys = ("tfl", "hongkong", "fintraffic")
    service = CameraCatalogueService(tuple(source(key) for key in keys), clock)

    with patch.object(service, "catalogue", wraps=service.catalogue) as catalogue:
        initial = await service.initial_catalogue(user)

    assert catalogue.call_args_list == [call(user, key) for key in keys]
    assert tuple(camera.provider for camera in initial.cameras) == keys
    assert initial.providers == service.snapshot(user).providers


async def test_initial_catalogue_without_providers(user: User, clock: FakeClock) -> None:
    service = CameraCatalogueService((), clock)

    result = await service.initial_catalogue(user)

    assert result.cameras == ()
    assert result.providers == ()


async def test_initial_catalogue_statuses_include_a_slower_provider(
    user: User, clock: FakeClock
) -> None:
    slow = source("tfl")
    fast = source("fintraffic")
    release_slow = asyncio.Event()
    fast_finished = asyncio.Event()
    cameras = slow.fetch.return_value

    async def slow_fetch() -> tuple[Camera, ...]:
        await release_slow.wait()
        return cameras

    slow.fetch.side_effect = slow_fetch
    service = CameraCatalogueService((slow, fast), clock)
    original_catalogue = service.catalogue

    async def tracked_catalogue(actor: User, provider: str) -> object:
        result = await original_catalogue(actor, provider)
        if provider == "fintraffic":
            fast_finished.set()
        return result

    with patch.object(service, "catalogue", side_effect=tracked_catalogue):
        pending = asyncio.create_task(service.initial_catalogue(user))
        try:
            await asyncio.wait_for(fast_finished.wait(), timeout=5)
        finally:
            release_slow.set()
        result = await pending

    assert tuple(status.status for status in result.providers) == ("available", "available")


@pytest.mark.parametrize(
    ("failed", "fetched", "has_camera", "expected"),
    [
        (False, False, False, "not_loaded"),
        (False, False, True, "not_loaded"),
        (True, False, False, "unavailable"),
        (True, False, True, "unavailable"),
        (False, True, False, "unavailable"),
        (True, True, False, "unavailable"),
        (False, True, True, "available"),
        (True, True, True, "stale"),
    ],
)
async def test_snapshot_and_catalogue_agree_on_provider_state(
    user: User,
    clock: FakeClock,
    failed: bool,
    fetched: bool,
    has_camera: bool,
    expected: str,
) -> None:
    service = CameraCatalogueService((source(),), clock)
    cached = service._sources[0]
    cached.failed = failed
    cached.fetched_at = clock.now() if fetched else None
    cached.cameras = tuple(cached.source.fetch.return_value) if has_camera else ()
    cached.retry_at = clock.now() + timedelta(minutes=1)

    snapshot = service.snapshot(user)
    refreshed = await service.catalogue(user)

    assert snapshot.providers[0].status == refreshed.providers[0].status == expected
    assert snapshot.cameras == refreshed.cameras

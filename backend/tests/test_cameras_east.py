"""Estonian DATEX index, curated eastern catalogues, registry uniqueness and the frame route."""

import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

import ase.application.cameras as cameras_module
from ase.adapters.geo.camera_east import (
    CURATED,
    ENDPOINT,
    EstoniaCameraSource,
    build_sources,
    curated,
    parse_estonia,
)
from ase.adapters.geo.camera_registry import build_sources as build_registry
from ase.application.cameras import CameraCatalogueService
from ase.container import Container
from ase.domain.cameras import Camera
from ase.domain.errors import RateLimited, Unauthenticated
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, login_token

FIXTURE = Path(__file__).parent / "fixtures" / "cameras" / "tarktee_locations.xml"
IMAGE = "https://tarktee.transpordiamet.ee/images/987/987_202609140351.jpg"


def test_datex_locations_become_exact_cameras_with_current_image_links() -> None:
    cameras = parse_estonia(FIXTURE.read_bytes())
    assert [camera.id for camera in cameras] == [
        "estonia:a84734fc-8f1d-47af-ba22-8323cd6eb367",
        "estonia:63b6d697-3070-45e7-aa38-95e3fd42a633",
    ]
    first = cameras[0]
    assert first.title == "Kaimi"
    assert (first.latitude, first.longitude) == (58.34474, 26.3853)
    assert first.snapshot_url == IMAGE
    assert first.coordinate_precision == "exact"
    assert first.source_url == "https://tarktee.mnt.ee/"
    assert "Transpordiamet" in first.attribution
    for payload in [b"<payload/>", b"not xml", b"<a><latitude>x</latitude></a>"]:
        with pytest.raises(ValueError, match="Estonian"):
            parse_estonia(payload)


async def test_source_uses_the_fixed_endpoint_without_redirects() -> None:
    http = AsyncMock()
    http.get_bytes.return_value = FIXTURE.read_bytes()
    assert len(await EstoniaCameraSource(http).fetch()) == 2
    http.get_bytes.assert_awaited_once_with(
        ENDPOINT, conditional=False, max_redirects=0, accept="application/xml"
    )


def test_curated_catalogues_keep_hosts_and_provenance() -> None:
    for provider in CURATED:
        cameras = curated(provider)
        assert cameras, provider
        assert len({camera.id for camera in cameras}) == len(cameras)
        assert all(camera.coordinate_precision == "approximate" for camera in cameras)
        if provider == "tallinn":
            assert all(
                str(camera.snapshot_url).startswith("https://ristmikud.tallinn.ee/last/cam")
                for camera in cameras
            )
            assert all(59.3 < camera.latitude < 59.6 for camera in cameras)
        else:
            assert all(
                str(camera.stream_url).startswith("https://www.youtube.com/embed/")
                and camera.stream_type == "iframe"
                for camera in cameras
            )
    assert len(curated("tallinn")) >= 200
    karbala = curated("iraq-iran-live")
    assert all(abs(camera.latitude - 32.616) < 0.01 for camera in karbala)
    assert all("Al-" in camera.attribution for camera in karbala)


async def test_registry_ids_stay_unique_with_the_new_modules() -> None:
    sources = build_registry(AsyncMock(), AsyncMock())
    ids = [source.id for source in sources]
    assert len(set(ids)) == len(ids)
    assert {"traffic-scotland", "durham", "uk-live", "estonia", "tallinn", "china-live"} <= set(ids)
    east = build_sources(AsyncMock())
    assert next(source.id for source in east) == "estonia"


class FrameSource:
    id = "traffic-scotland"
    name = "Traffic Scotland"

    def __init__(self, data: bytes | None = b"\xff\xd8\xffdata") -> None:
        self.data = data
        self.calls: list[str] = []

    async def fetch(self) -> tuple[Camera, ...]:
        return ()

    async def frame(self, frame_id: str) -> bytes | None:
        self.calls.append(frame_id)
        if frame_id == "boom":
            raise ValueError("provider failed")
        return self.data


class PlainSource:
    id = "plain"
    name = "Plain"

    async def fetch(self) -> tuple[Camera, ...]:
        return ()


class BlockingFrameSource(FrameSource):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def frame(self, frame_id: str) -> bytes | None:
        self.calls.append(frame_id)
        self.started.set()
        await self.release.wait()
        return self.data


async def test_service_frame_only_from_declaring_sources(user: User, clock: FakeClock) -> None:
    source = FrameSource()
    service = CameraCatalogueService((source, PlainSource()), clock)
    assert await service.frame(user, "traffic-scotland", "12") == b"\xff\xd8\xffdata"
    assert await service.frame(user, "plain", "12") is None
    assert (
        await CameraCatalogueService((FrameSource(b""),), clock).frame(
            user, "traffic-scotland", "1"
        )
        is None
    )
    with pytest.raises(ValueError, match="Unknown"):
        await service.frame(user, "missing", "12")
    with pytest.raises(Unauthenticated):
        await service.frame(replace(user, is_active=False), "plain", "1")


async def test_frame_work_is_coalesced_and_bounded_per_user(user: User, clock: FakeClock) -> None:
    source = BlockingFrameSource()
    service = CameraCatalogueService((source,), clock)
    first = asyncio.create_task(service.frame(user, source.id, "same"))
    await source.started.wait()
    second = asyncio.create_task(service.frame(user, source.id, "same"))
    await asyncio.sleep(0)
    with pytest.raises(RateLimited):
        await service.frame(user, source.id, "other")
    other_user = replace(user, id=uuid4())
    other = asyncio.create_task(service.frame(other_user, source.id, "other"))
    await asyncio.sleep(0)
    source.release.set()
    assert await asyncio.gather(first, second, other) == [source.data] * 3
    assert source.calls.count("same") == 1 and source.calls.count("other") == 1


async def test_hung_frame_reader_releases_work_admission(
    user: User, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = BlockingFrameSource()
    service = CameraCatalogueService((source,), clock)
    monkeypatch.setattr(cameras_module, "FRAME_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(TimeoutError):
        await service.frame(user, source.id, "hung")
    source.release.set()

    assert await service.frame(user, source.id, "next") == source.data
    assert source.calls == ["hung", "next"]


async def test_frame_route_is_authenticated_and_bounded(
    client: AsyncClient, container: Container, user: User
) -> None:
    source = FrameSource()
    container.cameras = CameraCatalogueService((source, PlainSource()), container.clock)
    path = "/api/cameras/frames/traffic-scotland/12.jpg"
    assert (await client.get(path)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(path, headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, max-age=30"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content == b"\xff\xd8\xffdata"
    assert (
        await client.get("/api/cameras/frames/plain/12.jpg", headers=headers)
    ).status_code == 404
    assert (await client.get("/api/cameras/frames/none/12.jpg", headers=headers)).status_code == 404
    assert (
        await client.get("/api/cameras/frames/traffic-scotland/boom.jpg", headers=headers)
    ).status_code == 503
    assert (
        await client.get("/api/cameras/frames/Bad_Provider/1.jpg", headers=headers)
    ).status_code == 404
    assert source.calls == ["12", "boom"]

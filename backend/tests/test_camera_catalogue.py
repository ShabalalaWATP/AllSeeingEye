"""Offline camera normalisation, cache and protected catalogue regressions."""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from ase.adapters.geo.cameras import (
    OfficialCameraSource,
    parse_fintraffic,
    parse_hongkong,
    parse_tfl,
    valid_snapshot,
)
from ase.application.cameras import CameraCatalogueService
from ase.container import Container
from ase.domain.cameras import Camera
from ase.domain.errors import Unauthenticated
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, login_token

IMAGE = "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/001.jpg"


def tfl(**changes: object) -> dict[str, object]:
    return {
        "id": "JamCams_001",
        "commonName": "Road camera",
        "lat": 51.5,
        "lon": -0.1,
        "additionalProperties": [{"key": "imageUrl", "value": IMAGE}],
        **changes,
    }


def test_tfl_validation_and_no_capture_timestamp_guess() -> None:
    data = [
        tfl(),
        tfl(),
        tfl(id="bad", lat="nan"),
        tfl(id="other", lon=181),
        tfl(id="missing", additionalProperties=[]),
        tfl(
            id="inactive",
            additionalProperties=[
                {"key": "available", "value": "false"},
                {"key": "imageUrl", "value": IMAGE},
            ],
        ),
        None,
        tfl(id="a/b"),
        tfl(id="null", lat=None),
    ]
    result = parse_tfl(json.dumps(data).encode())
    assert len(result) == 1
    assert result[0].id == "tfl:JamCams_001"
    assert result[0].captured_at is None
    with pytest.raises(ValueError):
        parse_tfl(b"{}")


@pytest.mark.parametrize(
    "url",
    [
        "http://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/001.jpg",
        "https://s3-eu-west-1.amazonaws.com/other/001.jpg",
        "https://s3-eu-west-1.amazonaws.com:443/jamcams.tfl.gov.uk/001.jpg",
        "https://evil.test/001.jpg",
        IMAGE + "?redirect=1",
        IMAGE + "#fragment",
        "https://user@s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/001.jpg",
        "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/../001.jpg",
    ],
)
def test_snapshot_allowlist_rejects_untrusted_destinations(url: str) -> None:
    assert not valid_snapshot("tfl", url)


def test_hongkong_authoritative_coordinates_and_safe_xml() -> None:
    valid = (
        "<image><key>H429F</key><description>Road &amp; bridge</description>"
        "<latitude>22.24845</latitude><longitude>114.1505</longitude>"
        "<url>https://tdcctv.data.one.gov.hk/H429F.JPG</url></image>"
    )
    result = parse_hongkong(
        ("<image-list>" + valid + valid.replace("22.24845", "51.5") + "</image-list>").encode()
    )
    assert len(result) == 1
    assert result[0].title == "Road & bridge"


def test_fintraffic_collection_and_preset_gates() -> None:
    feature = {
        "geometry": {"coordinates": [24, 60]},
        "properties": {
            "id": "C001",
            "name": "Weather camera",
            "collectionStatus": "GATHERING",
            "state": None,
            "presets": [
                {"id": "C00100", "inCollection": False},
                {"id": "C00101", "inCollection": True},
            ],
        },
    }
    features = [
        feature,
        None,
        {**feature, "geometry": {}},
        {**feature, "properties": {**feature["properties"], "state": "REPAIR_INTERRUPTED"}},
        {**feature, "properties": {**feature["properties"], "collectionStatus": "REMOVED"}},
        {**feature, "properties": {**feature["properties"], "presets": []}},
    ]
    result = parse_fintraffic(json.dumps({"features": features}).encode())
    assert len(result) == 1
    assert result[0].snapshot_url == "https://weathercam.digitraffic.fi/C00101.jpg"
    with pytest.raises(ValueError):
        parse_fintraffic(b"[]")


def source() -> AsyncMock:
    camera = Camera("tfl:001", "tfl", "Road", 51.5, -0.1, IMAGE, "https://tfl.gov.uk", "TfL")
    result = AsyncMock(id="tfl", fetch=AsyncMock(return_value=(camera,)))
    result.name = "TfL"
    return result


async def test_cache_coalesces_and_failed_refresh_is_bounded(user: User, clock: FakeClock) -> None:
    upstream = source()
    service = CameraCatalogueService((upstream,), clock)
    first, second = await asyncio.gather(service.catalogue(user), service.catalogue(user))
    assert first == second
    assert upstream.fetch.await_count == 1
    clock.advance(timedelta(minutes=16))
    upstream.fetch.side_effect = ValueError("private upstream details")
    result = await service.catalogue(user)
    assert result.providers[0].status == "stale"
    assert len(result.cameras) == 1
    assert "private" not in str(result)
    await service.catalogue(user)
    assert upstream.fetch.await_count == 2
    clock.advance(timedelta(days=2))
    expired = await service.catalogue(user)
    assert expired.cameras == ()
    assert expired.providers[0].status == "unavailable"


async def test_failure_isolated_empty_source_and_inactive_user(
    user: User, clock: FakeClock
) -> None:
    broken = source()
    broken.fetch.return_value = ()
    service = CameraCatalogueService((source(), broken), clock)
    result = await service.catalogue(user)
    assert len(result.cameras) == 1
    assert result.providers[1].status == "unavailable"
    with pytest.raises(Unauthenticated):
        await service.catalogue(replace(user, is_active=False))


async def test_adapter_fixed_endpoint_and_safe_parse_error() -> None:
    http = AsyncMock(get_bytes=AsyncMock(return_value=json.dumps([tfl()]).encode()))
    adapter = OfficialCameraSource("tfl", http)
    assert len(await adapter.fetch()) == 1
    http.get_bytes.assert_awaited_once_with(
        "https://api.tfl.gov.uk/Place/Type/JamCam", conditional=False, max_redirects=0
    )
    adapter = OfficialCameraSource("hongkong", http)
    http.get_bytes.return_value = b"<!DOCTYPE x [<!ENTITY a SYSTEM 'file:///private'>]><x>&a;</x>"
    with pytest.raises(ValueError, match="temporarily unavailable"):
        await adapter.fetch()


async def test_deep_json_is_isolated_as_a_provider_failure(user: User, clock: FakeClock) -> None:
    payload = b"[" * 20_000 + b"0" + b"]" * 20_000
    with pytest.raises(RecursionError):
        parse_tfl(payload)
    http = AsyncMock(get_bytes=AsyncMock(return_value=payload))
    adapter = OfficialCameraSource("tfl", http)
    result = await CameraCatalogueService((adapter, source()), clock).catalogue(user)
    assert result.providers[0].status == "unavailable"
    assert result.providers[1].status == "available"
    assert len(result.cameras) == 1


async def test_authenticated_route(client: AsyncClient, container: Container, user: User) -> None:
    container.cameras = CameraCatalogueService((source(),), container.clock)
    assert (await client.get("/api/cameras")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/cameras", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["cameras"][0]["snapshot_url"] == IMAGE


async def test_source_result_cap(user: User, clock: FakeClock) -> None:
    upstream = source()
    camera = upstream.fetch.return_value[0]
    upstream.fetch.return_value = tuple(replace(camera, id=f"tfl:{i}") for i in range(1600))
    result = await CameraCatalogueService((upstream,), clock).catalogue(user)
    assert len(result.cameras) == 1500
    assert result.providers[0].count == 1500


async def test_session_expiry_during_fetch_denies_release(
    client: AsyncClient,
    container: Container,
    user: User,
    clock: FakeClock,
) -> None:
    upstream = source()
    camera = upstream.fetch.return_value[0]

    async def expire():
        clock.advance(timedelta(days=1))
        return (camera,)

    upstream.fetch.side_effect = expire
    container.cameras = CameraCatalogueService((upstream,), clock)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    result = await client.get("/api/cameras", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 401

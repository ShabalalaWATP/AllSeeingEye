"""Place lookup privacy, provider admission and bounded parsing, no live network."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from ase.adapters.routing.photon import PhotonPlaceSearchGateway, parse_places
from ase.application.place_search import PlaceSearch
from ase.domain.errors import InvalidRequest, RateLimited
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


def payload():
    return {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-1.2, 51.7]},
                "properties": {"name": "Oxford", "city": "Oxford", "country": "UK"},
            }
        ]
    }


def test_place_labels_and_empty_results():
    places = parse_places(json.dumps(payload()).encode())
    assert places[0].label == "Oxford, UK" and places[0].point.lon == -1.2
    assert parse_places(b'{"features": []}') == ()


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(features=[data["features"][0]] * 6),
        lambda data: data["features"][0]["geometry"].update(type="LineString"),
        lambda data: data["features"][0]["geometry"].update(coordinates=[True, 2]),
        lambda data: data["features"][0]["geometry"].update(coordinates=[181, 2]),
        lambda data: data["features"][0]["geometry"].update(coordinates=[float("nan"), 2]),
        lambda data: data["features"][0]["properties"].update(name="x" * 201),
    ],
)
def test_invalid_places_rejected(change):
    data = payload()
    change(data)
    with pytest.raises(ValueError):
        parse_places(json.dumps(data).encode())


async def test_provider_fixed_origin_and_redacted_url():
    http = Mock(get_secret_bytes=AsyncMock(return_value=json.dumps(payload()).encode()))
    await PhotonPlaceSearchGateway(http).search("Oxford station")
    target = http.get_secret_bytes.call_args.args[0]
    url = urlsplit(target.url)
    assert url.scheme == "https" and url.netloc == "photon.komoot.io" and url.path == "/api/"
    assert parse_qs(url.query)["q"] == ["Oxford station"]
    assert "Oxford" not in repr(target)


async def test_admission_and_redacted_errors():
    limiter = Mock()
    limiter.hit.return_value = None
    gateway = Mock(search=AsyncMock(side_effect=RuntimeError("private address")))
    service = PlaceSearch(gateway, limiter)
    with pytest.raises(InvalidRequest):
        await service.search(uuid4(), "x")
    gateway.search.assert_not_called()
    limiter.hit.return_value = 2
    with pytest.raises(RateLimited):
        await service.search(uuid4(), "Oxford")
    gateway.search.assert_not_called()
    limiter.hit.return_value = None
    with pytest.raises(InvalidRequest, match="Address search unavailable") as error:
        await service.search(uuid4(), "Oxford")
    assert "private address" not in str(error.value)


async def test_concurrent_requests_refused_and_cancel_releases_slot():
    entered, finish = asyncio.Event(), asyncio.Event()

    async def wait(*args):
        entered.set()
        await finish.wait()
        return ()

    limiter = Mock()
    limiter.hit.return_value = None
    service = PlaceSearch(Mock(search=AsyncMock(side_effect=wait)), limiter)
    task = asyncio.create_task(service.search(uuid4(), "Oxford"))
    await entered.wait()
    with pytest.raises(RateLimited):
        await service.search(uuid4(), "London")
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    finish.set()
    assert await service.search(uuid4(), "Oxford") == ()


async def test_api_auth_body_bounds_and_session_recheck(client, container, user, monkeypatch):
    search = AsyncMock(return_value=parse_places(json.dumps(payload()).encode()))
    monkeypatch.setattr(container.place_search, "search", search)
    assert (
        await client.post("/api/navigation/places", json={"query": "Oxford"})
    ).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    for body in ({"query": "x"}, {"query": "Oxford", "url": "https://bad.invalid"}):
        assert (
            await client.post("/api/navigation/places", json=body, headers=headers)
        ).status_code == 422
    assert (
        await client.post(
            "/api/navigation/places",
            content=b" " * 2049,
            headers={**headers, "Content-Type": "application/json"},
        )
    ).status_code == 422
    search.assert_not_called()
    result = await client.post("/api/navigation/places", json={"query": "Oxford"}, headers=headers)
    assert result.status_code == 200 and result.json()[0]["label"] == "Oxford, UK"
    assert result.headers["cache-control"] == "private, no-store"

    async def logout(*args):
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await session.commit()
        return ()

    search.side_effect = logout
    assert (
        await client.post("/api/navigation/places", json={"query": "Oxford"}, headers=headers)
    ).status_code == 401

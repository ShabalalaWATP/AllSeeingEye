"""Terrain batch admission, request bounds, authentication and post-egress checks."""

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.api.routers import terrain as terrain_api
from ase.application.terrain import TerrainSampler
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.events import Point
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

POSITIONS = (Point(0, 0), Point(0.01, 0))
BODY = {"positions": [{"lon": 0, "lat": 0}, {"lon": 0.01, "lat": 0}]}


async def test_bounds_before_network_and_redacted_provider_error():
    limiter = Mock()
    limiter.hit.return_value = None
    gateway = Mock(elevations=AsyncMock(return_value=(1, -2)))
    service = TerrainSampler(gateway, limiter)
    for positions in ((), POSITIONS * 501, (Point(0, 90),), tuple(Point(i, 0) for i in range(65))):
        with pytest.raises(InvalidRequest):
            await service.sample(uuid4(), positions)
    gateway.elevations.assert_not_called()
    assert await service.sample(uuid4(), POSITIONS) == (1, -2)
    gateway.elevations.return_value = (1,)
    with pytest.raises(InvalidRequest, match="No missing heights"):
        await service.sample(uuid4(), POSITIONS)
    gateway.elevations.side_effect = RuntimeError("private coordinates")
    with pytest.raises(InvalidRequest) as error:
        await service.sample(uuid4(), POSITIONS)
    assert "private coordinates" not in str(error.value)
    limiter.hit.return_value = 3
    with pytest.raises(RateLimited):
        await service.sample(uuid4(), POSITIONS)
    limiter.hit.side_effect = [None, 4]
    with pytest.raises(RateLimited):
        await service.sample(uuid4(), POSITIONS)


async def test_two_active_batches_and_cancellation_releases_slot():
    active = 0
    entered, release = asyncio.Event(), asyncio.Event()

    async def wait(*args):
        nonlocal active
        active += 1
        if active == 2:
            entered.set()
        await release.wait()
        return (1, 2)

    limiter = Mock()
    limiter.hit.return_value = None
    service = TerrainSampler(Mock(elevations=AsyncMock(side_effect=wait)), limiter)
    first = asyncio.create_task(service.sample(uuid4(), POSITIONS))
    second = asyncio.create_task(service.sample(uuid4(), POSITIONS))
    await entered.wait()
    with pytest.raises(RateLimited):
        await service.sample(uuid4(), POSITIONS)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    release.set()
    assert await second == (1, 2)
    assert await service.sample(uuid4(), POSITIONS) == (1, 2)
    assert service._active == 0


async def test_api_request_bounds_and_current_session(client, container, user, monkeypatch):
    sample = AsyncMock(return_value=(10.5, -20))
    monkeypatch.setattr(container.terrain_sampler, "sample", sample)
    assert (await client.post("/api/terrain/elevations", json=BODY)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    invalid = [
        {"positions": []},
        {"positions": BODY["positions"] * 501},
        {"positions": [{"lon": True, "lat": 0}]},
        {"positions": [{"lon": 181, "lat": 0}]},
        {"positions": [{"lon": 0, "lat": 86}]},
        {**BODY, "url": "http://127.0.0.1"},
    ]
    for body in invalid:
        assert (
            await client.post("/api/terrain/elevations", json=body, headers=headers)
        ).status_code == 422
    assert (
        await client.post(
            "/api/terrain/elevations",
            content=b" " * 65537,
            headers={**headers, "Content-Type": "application/json"},
        )
    ).status_code == 413
    assert (
        await client.post("/api/terrain/elevations", content=b"{}", headers=headers)
    ).status_code == 422
    sample.assert_not_called()
    with monkeypatch.context() as limited:
        limited.setattr(terrain_api, "MAX_BODY_BYTES", 20)
        assert (
            await client.post("/api/terrain/elevations", json=BODY, headers=headers)
        ).status_code == 422
    response = await client.post("/api/terrain/elevations", json=BODY, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["elevations_m"] == [10.5, -20] and data["zoom"] == 10
    assert 152 < data["resolution_m"] < 153
    assert response.headers["cache-control"] == "private, no-store"

    async def logout(*args):
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await session.commit()
        return (1, 2)

    sample.side_effect = logout
    assert (
        await client.post("/api/terrain/elevations", json=BODY, headers=headers)
    ).status_code == 401

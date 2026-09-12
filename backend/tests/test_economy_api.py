"""Economics data is private to current sessions and does not call the report pipeline."""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from unittest.mock import AsyncMock

from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.api.routers import economy as economy_api
from ase.domain.economy import EconomySnapshot
from ase.domain.economy_catalogue import empty_fx, empty_regions
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_economy_data import parse_world_bank, wb_payload


async def test_login_no_store_and_session_recheck(client, container, user, monkeypatch):
    now = container.clock.now()
    snapshot = EconomySnapshot(now, now + timedelta(hours=1), empty_regions(), empty_fx())
    load = AsyncMock(return_value=snapshot)
    monkeypatch.setattr(container.economy, "snapshot", load)
    assert (await client.get("/api/economy")).status_code == 401
    load.assert_not_awaited()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    result = await client.get("/api/economy", headers=bearer(token))
    assert result.status_code == 200 and len(result.json()["regions"]) == 6
    assert result.headers["cache-control"] == "private, no-store"

    async def expired():
        container.clock.advance(timedelta(hours=1))
        return snapshot

    load.side_effect = expired
    assert (await client.get("/api/economy", headers=bearer(token))).status_code == 401


async def test_disable_during_collection_cannot_release_cached_provider_values(
    client, container, user, monkeypatch
):
    now, entered, release = container.clock.now(), asyncio.Event(), asyncio.Event()
    snapshot = EconomySnapshot(
        now,
        now + timedelta(hours=1),
        parse_world_bank(wb_payload(), now),
        empty_fx(),
    )

    async def collection():
        entered.set()
        await release.wait()
        return snapshot

    monkeypatch.setattr(container.economy, "snapshot", collection)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    request = asyncio.create_task(client.get("/api/economy", headers=bearer(token)))
    await entered.wait()
    async with container.source_admission.guard(), container.session_factory() as session:
        await SqlSourceControlRepository(session).set("research-world-bank", False, now, user.id)
        await session.commit()
    release.set()
    response = await request
    assert response.status_code == 200
    gdp = response.json()["regions"][1]["series"][0]
    assert gdp["status"] == "unavailable" and gdp["points"] == []
    assert "disabled by the administrator" in gdp["note"]


async def test_source_release_guard_covers_final_filter_and_session_check_only(
    client, container, user, monkeypatch
):
    held = False
    original_guard = container.source_admission.guard
    original_filter = container.economy.refilter
    original_session = economy_api.validate_request_session
    now = container.clock.now()

    @asynccontextmanager
    async def guard():
        nonlocal held
        async with original_guard():
            held = True
            try:
                yield
            finally:
                held = False

    async def collection():
        assert not held
        return EconomySnapshot(now, now + timedelta(hours=1), empty_regions(), empty_fx())

    async def refilter(snapshot):
        assert held
        return await original_filter(snapshot)

    async def session_check(*args):
        assert held
        await original_session(*args)

    monkeypatch.setattr(container.source_admission, "guard", guard)
    monkeypatch.setattr(container.economy, "snapshot", collection)
    monkeypatch.setattr(container.economy, "refilter", refilter)
    monkeypatch.setattr(economy_api, "validate_request_session", session_check)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/economy", headers=bearer(token))
    assert response.status_code == 200 and not held

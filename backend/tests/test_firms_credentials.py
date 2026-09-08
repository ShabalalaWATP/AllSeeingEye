"""Encrypted FIRMS administrator lifecycle and stale authority/test rejection."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select, update

from ase.adapters.feeds.firms_runtime import FirmsConnectionProbe
from ase.adapters.persistence.firms_credentials import FirmsCredentialRow, SqlFirmsCredentials
from ase.adapters.persistence.models import UserRow
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, RateLimited, Unauthenticated
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from team_helpers import CONTEXT
from test_saved_map_views import claims_for

KEY = "k" * 32  # Deliberately synthetic; shared by mocked probes and disposable database tests.
BASE = "/api/admin/sources/firms_viirs_noaa20/connection"


async def call(container, actor, method, *args):
    async with container.session_factory() as session:
        return await getattr(container.admin_firms_credentials(session), method)(actor, *args)


@pytest.fixture
def probe(monkeypatch):
    fake = AsyncMock(return_value=3)
    monkeypatch.setattr(FirmsConnectionProbe, "test", fake)
    return fake


async def ready(container, actor):
    state = await call(container, actor, "get")
    state = await call(container, actor, "draft", KEY, state.revision, CONTEXT)
    result = await call(container, actor, "test", state.revision, CONTEXT)
    return result.status


async def test_api_masked_encrypted_confirm_and_clear(client, container, admin, probe):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = bearer(token)
    status = await client.get(BASE, headers=headers)
    assert status.status_code == 200 and "no-store" in status.headers["cache-control"]
    assert status.json()["revision"] == 0 and not status.json()["configured"]
    draft = await client.put(
        BASE + "/draft", headers=headers, json={"api_key": KEY, "expected_revision": 0}
    )
    assert draft.status_code == 200 and KEY not in draft.text
    async with container.session_factory() as session:
        row = await session.get(FirmsCredentialRow, 1)
        assert row.draft_encrypted != KEY and container.cipher.decrypt(row.draft_encrypted) == KEY
        assert row.active_encrypted is None
    tested = await client.post(BASE + "/test", headers=headers, json={"expected_revision": 1})
    assert tested.status_code == 200 and tested.json()["ok"]
    assert container.store.stats().total == 0
    confirmed = await client.post(
        BASE + "/confirm",
        headers=headers,
        json={
            "expected_revision": 1,
            "test_generation": tested.json()["status"]["test_generation"],
        },
    )
    assert confirmed.status_code == 200 and confirmed.json()["credential_origin"] == "database"
    assert confirmed.json()["active_revision"] == 1 and not confirmed.json()["draft_present"]
    cleared = await client.request("DELETE", BASE, headers=headers, json={"expected_revision": 2})
    assert cleared.status_code == 200 and not cleared.json()["configured"]
    assert KEY not in cleared.text


@pytest.mark.parametrize(
    "key", ["short", "x" * 129, "invalid key with spaces", "https://secret.example/token"]
)
async def test_invalid_input_never_echoes_credentials(client, admin, key):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.put(
        BASE + "/draft", headers=bearer(token), json={"api_key": key, "expected_revision": 0}
    )
    assert response.status_code == 422 and key not in response.text


async def test_non_admin_and_revoked_actor_cannot_use_connection(
    client, container, admin, user, probe
):
    actor = await claims_for(client, container, user)
    with pytest.raises(Forbidden):
        await call(container, actor, "get")
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    async with container.session_factory() as session:
        await session.execute(update(UserRow).where(UserRow.id == admin.id).values(is_active=False))
        await session.commit()
    with pytest.raises(Unauthenticated):
        await call(container, actor, "confirm", state.revision, state.test_generation, CONTEXT)


async def test_expired_edited_and_other_session_proofs_refused(
    client, container, admin, probe, clock
):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    other = await claims_for(client, container, admin)
    with pytest.raises(Conflict):
        await call(container, other, "confirm", state.revision, state.test_generation, CONTEXT)
    state2 = await call(container, actor, "draft", KEY + "new", state.revision, CONTEXT)
    with pytest.raises(Conflict):
        await call(container, actor, "confirm", state.revision, state.test_generation, CONTEXT)
    result = await call(container, actor, "test", state2.revision, CONTEXT)
    clock.advance(timedelta(minutes=16))
    # Token expiry is also authoritative; a new authenticated session cannot reuse old proof.
    fresh = await claims_for(client, container, admin)
    with pytest.raises(Conflict):
        await call(
            container,
            fresh,
            "confirm",
            result.status.revision,
            result.status.test_generation,
            CONTEXT,
        )


async def test_failed_retest_invalidates_success_without_touching_active(
    client, container, admin, probe
):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    await call(container, actor, "confirm", state.revision, state.test_generation, CONTEXT)
    state = await ready(container, actor)
    probe.side_effect = RuntimeError(KEY)
    failed = await call(container, actor, "test", state.revision, CONTEXT)
    assert not failed.ok and KEY not in repr(failed)
    assert failed.status.configured and not failed.status.test_ok
    with pytest.raises(Conflict):
        await call(container, actor, "confirm", state.revision, state.test_generation, CONTEXT)


@pytest.mark.parametrize("mutation", ["edit", "revoke", "newer_test"])
async def test_test_rechecks_state_after_io(client, container, admin, probe, mutation):
    actor = await claims_for(client, container, admin)
    draft = await call(container, actor, "draft", KEY, 0, CONTEXT)

    async def change(*args):
        if mutation == "edit":
            await call(container, actor, "draft", KEY + "changed", draft.revision, CONTEXT)
        elif mutation == "revoke":
            async with container.session_factory() as session:
                await session.execute(
                    update(UserRow).where(UserRow.id == admin.id).values(is_active=False)
                )
                await session.commit()
        else:
            probe.side_effect = RuntimeError("Safe synthetic upstream failure")
            await call(container, actor, "test", draft.revision, CONTEXT)
        return 2

    probe.side_effect = change
    with pytest.raises(Unauthenticated if mutation == "revoke" else Conflict):
        await call(container, actor, "test", draft.revision, CONTEXT)
    async with container.session_factory() as session:
        assert (await session.get(FirmsCredentialRow, 1)).tested_at is None


async def test_cancelled_test_leaves_no_activation_proof(client, container, admin, probe):
    actor = await claims_for(client, container, admin)
    await call(container, actor, "draft", KEY, 0, CONTEXT)
    probe.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await call(container, actor, "test", 1, CONTEXT)
    async with container.session_factory() as session:
        assert (await session.get(FirmsCredentialRow, 1)).tested_at is None


async def test_environment_and_encryption_policy(client, container, admin, probe, monkeypatch):
    actor = await claims_for(client, container, admin)
    container.settings.firms_map_key = SecretStr(KEY)
    original = SqlFirmsCredentials.get
    monkeypatch.setattr(
        SqlFirmsCredentials,
        "get",
        AsyncMock(side_effect=AssertionError("Environment status must not need credential table")),
    )
    status = await call(container, actor, "get")
    assert status.credential_origin == "environment"
    with pytest.raises(InvalidRequest):
        await call(container, actor, "draft", KEY, 0, CONTEXT)
    monkeypatch.setattr(SqlFirmsCredentials, "get", original)
    container.settings.firms_map_key = None
    container.cipher = type(container.cipher)(None)
    with pytest.raises(InvalidRequest):
        await call(container, actor, "draft", KEY, 0, CONTEXT)
    async with container.session_factory() as session:
        assert await session.scalar(select(FirmsCredentialRow)) is None


@pytest.mark.parametrize("operation", ["get", "confirm"])
async def test_actual_logout_during_repository_read_denies_later_release(
    client, container, admin, probe, monkeypatch, operation
):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    refresh_secret = client.cookies.get("ase_refresh")
    assert refresh_secret
    original = SqlFirmsCredentials.get

    async def get_then_logout(repository):
        row = await original(repository)
        async with container.session_factory() as session:
            await container.logout(session).execute(refresh_secret, CONTEXT)
        return row

    monkeypatch.setattr(SqlFirmsCredentials, "get", get_then_logout)
    with pytest.raises(Unauthenticated):
        if operation == "get":
            await call(container, actor, "get")
        else:
            await call(container, actor, "confirm", state.revision, state.test_generation, CONTEXT)
    async with container.session_factory() as session:
        assert (await session.get(FirmsCredentialRow, 1)).active_encrypted is None


async def test_expiry_during_status_preparation_denies_metadata(
    client, container, admin, probe, monkeypatch, clock
):
    actor = await claims_for(client, container, admin)
    original = SqlFirmsCredentials.get

    async def expired(repository):
        row = await original(repository)
        clock.advance(timedelta(minutes=16))
        return row

    monkeypatch.setattr(SqlFirmsCredentials, "get", expired)
    with pytest.raises(Unauthenticated):
        await call(container, actor, "get")


async def test_probe_deadline_returns_fixed_failure_without_proof(
    client, container, admin, probe, monkeypatch
):
    actor = await claims_for(client, container, admin)
    await call(container, actor, "draft", KEY, 0, CONTEXT)
    timeout = asyncio.timeout
    requested = []

    def bounded(seconds):
        requested.append(seconds)
        return timeout(0.01 if seconds == 20 else seconds)

    async def slow(*args):
        await asyncio.sleep(1)
        return 0

    monkeypatch.setattr(asyncio, "timeout", bounded)
    probe.side_effect = slow
    result = await call(container, actor, "test", 1, CONTEXT)
    assert 20 in requested and not result.ok and not result.status.test_ok
    assert result.fetched == 0 and KEY not in repr(result)


async def test_probe_rate_limit_blocks_fourth_network_attempt(client, container, admin, probe):
    actor = await claims_for(client, container, admin)
    await call(container, actor, "draft", KEY, 0, CONTEXT)
    for _ in range(3):
        assert (await call(container, actor, "test", 1, CONTEXT)).ok
    with pytest.raises(RateLimited):
        await call(container, actor, "test", 1, CONTEXT)
    assert probe.await_count == 3

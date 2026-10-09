"""Idle expiry cannot be bypassed by an existing JWT, stale heartbeat or release cache."""

import asyncio
import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow, RefreshTokenRow
from ase.api.routers import stream as stream_router
from ase.api.session_fence import SessionFence
from ase.domain.errors import SessionIdleExpired
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    csrf_headers,
    login,
)


@pytest.mark.parametrize("trigger", ["activity", "refresh", "logout", "idle_logout"])
async def test_expiry_cannot_revive_and_audits_once(client, user, container, clock, trigger):
    container.settings.session_idle_minutes = 5
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    token = signed_in.json()["access_token"]
    headers = {**bearer(token), **csrf_headers(client), "x-ase-activity": "1"}
    idle_logout = trigger == "idle_logout"
    if idle_logout:
        headers.update(
            {
                "x-ase-session-family": str(container.issuer.verify(token).family_id),
                "x-ase-idle-expired": "1",
            }
        )
        trigger = "logout"
    clock.advance(timedelta(minutes=5))
    denied = await client.get("/api/me", headers=bearer(token))
    assert denied.status_code == 401
    assert denied.json()["error"]["fields"] == {"idle_minutes": "5"}
    response = await client.post(f"/api/auth/{trigger}", headers=headers)
    assert response.status_code == (204 if trigger == "logout" else 401)
    if idle_logout:
        assert "set-cookie" not in response.headers
    await client.post("/api/auth/activity", headers=headers)
    async with container.session_factory() as session:
        audits = list(await session.scalars(select(AuditLogRow.action)))
        assert audits.count("session.idle_expired") == 1
        assert all(t.revoked_at is not None for t in await session.scalars(select(RefreshTokenRow)))


async def test_admin_override_uses_live_role_without_extending_ordinary_sessions(
    client,
    admin,
    user,
    container,
    clock,
):
    container.settings.admin_session_idle_minutes = 5
    administrator = await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    ordinary = await login(client, USER_EMAIL, USER_PASSWORD)
    assert administrator.json()["activity"]["idle_minutes"] == 5
    assert ordinary.json()["activity"]["idle_minutes"] == 180
    clock.advance(timedelta(minutes=5))
    assert (
        await client.get("/api/me", headers=bearer(administrator.json()["access_token"]))
    ).status_code == 401
    assert (
        await client.get("/api/me", headers=bearer(ordinary.json()["access_token"]))
    ).status_code == 200


async def test_cached_fence_observes_exact_idle_deadline_and_preserves_transaction(
    client,
    user,
    container,
    clock,
):
    container.settings.session_idle_minutes = 5
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    claims = container.issuer.verify(signed_in.json()["access_token"])
    fence = SessionFence(container, claims)
    clock.advance(timedelta(minutes=5) - timedelta(microseconds=1))
    await fence.confirm()
    clock.advance(timedelta(microseconds=1))
    with pytest.raises(SessionIdleExpired):
        fence.assert_live()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        pending = await repos.users.get_by_id(user.id)
        pending.display_name = "Must roll back"
        await repos.users.save(pending)
        with pytest.raises(SessionIdleExpired):
            await fence.confirm(session=session)
    async with container.session_factory() as session:
        assert (
            await container.repositories(session).users.get_by_id(user.id)
        ).display_name == user.display_name


@pytest.mark.parametrize("idle_only", [False, True])
async def test_cross_tab_cookie_replacement_cannot_change_heartbeat_or_idle_logout_owner(
    client,
    user,
    container,
    clock,
    idle_only,
):
    first = await login(client, USER_EMAIL, USER_PASSWORD)
    first_token = first.json()["access_token"]
    first_claims = container.issuer.verify(first_token)
    second = await login(client, USER_EMAIL, USER_PASSWORD)
    second_claims = container.issuer.verify(second.json()["access_token"])
    clock.advance(timedelta(minutes=1))
    response = await client.post(
        "/api/auth/activity", headers={**bearer(first_token), **csrf_headers(client)}
    )
    assert response.status_code == 200
    async with container.session_factory() as session:
        repo = container.repositories(session).refresh_tokens
        first_activity = await repo.activity(user.id, first_claims.family_id, clock.now())
        second_activity = await repo.activity(user.id, second_claims.family_id, clock.now())
        assert first_activity.last_activity_at > second_activity.last_activity_at
    response = await client.post(
        "/api/auth/logout",
        headers={
            **csrf_headers(client),
            "x-ase-session-family": str(first_claims.family_id),
            **({"x-ase-idle-expired": "1"} if idle_only else {}),
        },
    )
    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 200


async def test_stale_tab_idle_logout_preserves_activity_confirmed_by_another_tab(
    client, user, container, clock
):
    container.settings.session_idle_minutes = 5
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    token = signed_in.json()["access_token"]
    family = container.issuer.verify(token).family_id
    # A suspended tab misses this heartbeat, then resumes at its original deadline.
    clock.advance(timedelta(minutes=4))
    updated = await client.post(
        "/api/auth/activity", headers={**bearer(token), **csrf_headers(client)}
    )
    clock.advance(timedelta(minutes=1))
    stale = await client.post(
        "/api/auth/logout",
        headers={
            **csrf_headers(client),
            "x-ase-session-family": str(family),
            "x-ase-idle-expired": "1",
        },
    )
    assert stale.status_code == 200
    assert "set-cookie" not in stale.headers
    assert stale.json()["last_activity_at"] == updated.json()["last_activity_at"]
    assert stale.json()["idle_expires_at"] == updated.json()["idle_expires_at"]
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 200
    # The explicit Sign out choice remains unconditional.
    assert (
        await client.post(
            "/api/auth/logout",
            headers={**csrf_headers(client), "x-ase-session-family": str(family)},
        )
    ).status_code == 204
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 401


async def test_conditional_logout_without_family_binding_leaves_cookie_session_intact(client, user):
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/auth/logout", headers={**csrf_headers(client), "x-ase-idle-expired": "1"}
    )
    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    assert (
        await client.get("/api/me", headers=bearer(signed_in.json()["access_token"]))
    ).status_code == 200


async def test_idle_stream_emits_access_changed_and_ends_without_background_activity(
    client,
    user,
    container,
    clock,
    monkeypatch,
):
    container.settings.session_idle_minutes = 5
    monkeypatch.setattr(stream_router, "PING_SECONDS", 0.01)
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    token = signed_in.json()["access_token"]
    response = await stream_router.stream(user, container.issuer.verify(token), container)
    iterator = response.body_iterator
    try:
        assert (await anext(iterator))["event"] == "hello"
        clock.advance(timedelta(minutes=5))
        async with asyncio.timeout(2):
            assert (await anext(iterator))["event"] == "access.changed"
            frame = await anext(iterator)
        assert frame["event"] == "bye"
        assert json.loads(frame["data"])["reason"] == "session_idle_expired"
    finally:
        await iterator.aclose()
    assert container.streams.held(user.id) == 0

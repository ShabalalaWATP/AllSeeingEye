"""Refresh rotation, reuse detection, CSRF and logout."""

from __future__ import annotations

from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import (
    CSRF_COOKIE,
    REFRESH_COOKIE,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    csrf_headers,
    login,
    override_cookie,
    restore_session,
    set_cookie_headers,
)


async def test_refresh_rotates_the_token(client: AsyncClient, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    first = client.cookies.get(REFRESH_COOKIE)
    response = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert response.status_code == 200
    assert response.json()["user"]["email"] == USER_EMAIL
    second = client.cookies.get(REFRESH_COOKIE)
    assert second and second != first


async def test_reuse_of_a_rotated_token_revokes_the_family(client: AsyncClient, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    old = client.cookies.get(REFRESH_COOKIE) or ""
    csrf = client.cookies.get(CSRF_COOKIE) or ""
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 200
    latest = client.cookies.get(REFRESH_COOKIE) or ""
    headers = restore_session(client, old, csrf)
    reuse = await client.post("/api/auth/refresh", headers=headers)
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "invalid_refresh"
    headers = restore_session(client, latest, csrf)
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 401


async def test_refresh_requires_csrf(client: AsyncClient, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    missing = await client.post("/api/auth/refresh")
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "csrf_failed"
    wrong = await client.post("/api/auth/refresh", headers={"X-CSRF-Token": "nope"})
    assert wrong.status_code == 403


async def test_refresh_without_cookie_fails(client: AsyncClient) -> None:
    override_cookie(client, CSRF_COOKIE, "abc")
    response = await client.post("/api/auth/refresh", headers={"X-CSRF-Token": "abc"})
    assert response.status_code == 401


async def test_refresh_with_unknown_token_fails(client: AsyncClient) -> None:
    override_cookie(client, CSRF_COOKIE, "abc")
    override_cookie(client, REFRESH_COOKIE, "never-issued", path="/api/auth")
    response = await client.post("/api/auth/refresh", headers={"X-CSRF-Token": "abc"})
    assert response.status_code == 401


async def test_refresh_expires(client: AsyncClient, user: User, clock: FakeClock) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    clock.advance(timedelta(days=15))
    response = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert response.status_code == 401


async def test_refresh_fails_for_deactivated_user(
    client: AsyncClient, user: User, container: Container
) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        stored = await repos.users.get_by_id(user.id)
        assert stored is not None
        stored.is_active = False
        await repos.users.save(stored)
        await repos.uow.commit()
    response = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert response.status_code == 401


async def test_logout_revokes_and_clears(client: AsyncClient, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    refresh = client.cookies.get(REFRESH_COOKIE) or ""
    csrf = client.cookies.get(CSRF_COOKIE) or ""
    response = await client.post("/api/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 204
    cleared = set_cookie_headers(response)
    assert any(c.startswith("ase_refresh=") and "Max-Age=0" in c for c in cleared)
    assert client.cookies.get(REFRESH_COOKIE) is None
    # Even a copy of the old cookie is useless now: the family was revoked.
    headers = restore_session(client, refresh, csrf)
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 401


async def test_logout_without_session_is_still_204(client: AsyncClient) -> None:
    override_cookie(client, CSRF_COOKIE, "abc")
    response = await client.post("/api/auth/logout", headers={"X-CSRF-Token": "abc"})
    assert response.status_code == 204
    override_cookie(client, REFRESH_COOKIE, "never-issued", path="/api/auth")
    response = await client.post("/api/auth/logout", headers={"X-CSRF-Token": "abc"})
    assert response.status_code == 204


async def test_logout_requires_csrf(client: AsyncClient, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.post("/api/auth/logout")).status_code == 403

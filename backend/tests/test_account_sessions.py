"""Session metadata and revocation remain strictly scoped to the bearer account."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.account_sessions import SqlAccountSessionRepository
from ase.container import Container
from ase.domain.errors import Unauthenticated
from ase.domain.tokens import RefreshToken
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    csrf_headers,
    login,
    login_token,
)


@pytest.mark.parametrize("admin_session", [False, True])
async def test_only_own_sessions_and_foreign_revocation_denied(
    client: AsyncClient,
    user: User,
    admin: User,
    admin_session: bool,
) -> None:
    other = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    ordinary = await login_token(client, USER_EMAIL, USER_PASSWORD)
    own, foreign = (other, ordinary) if admin_session else (ordinary, other)
    foreign_list = await client.get("/api/me/sessions", headers=bearer(foreign))
    foreign_id = foreign_list.json()["items"][0]["id"]
    response = await client.get("/api/me/sessions", headers=bearer(own))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert len(response.json()["items"]) == 1
    row = response.json()["items"][0]
    assert row["current"] is True
    assert row["id"] != foreign_id
    assert set(row) == {
        "id",
        "current",
        "created_at",
        "last_active_at",
        "expires_at",
        "user_agent",
        "ip",
    }
    for target in [foreign_id, str(uuid4())]:
        denied = await client.delete(f"/api/me/sessions/{target}", headers=bearer(own))
        assert denied.status_code == 404
    assert (await client.get("/api/me/sessions", headers=bearer(foreign))).status_code == 200


async def test_revoke_others_keeps_presented_family_and_blocks_access_and_refresh(
    client: AsyncClient,
    user: User,
) -> None:
    current = await login_token(client, USER_EMAIL, USER_PASSWORD)
    other = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post("/api/me/sessions/revoke-others", headers=bearer(current))
    assert response.status_code == 204
    assert (await client.get("/api/me/sessions", headers=bearer(other))).status_code == 401
    remaining = await client.get("/api/me/sessions", headers=bearer(current))
    assert len(remaining.json()["items"]) == 1
    # The browser cookie is the other login, but the explicit bearer selects the keeper.
    refresh = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert refresh.status_code == 401
    assert (await client.get("/api/me/sessions", headers=bearer(current))).status_code == 200


async def test_revoke_current_clears_cookies_and_ends_original_access(
    client: AsyncClient,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    page = await client.get("/api/me/sessions", headers=bearer(token))
    family = page.json()["items"][0]["id"]
    response = await client.delete(f"/api/me/sessions/{family}", headers=bearer(token))
    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert (await client.get("/api/me/sessions", headers=bearer(token))).status_code == 401
    assert (
        await client.post("/api/me/sessions/revoke-others", headers=bearer(token))
    ).status_code == 401


async def test_rotations_group_as_one_session_and_expired_families_are_hidden(
    client: AsyncClient,
    user: User,
    clock: FakeClock,
) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    original_time = clock.now()
    clock.advance(timedelta(seconds=30))
    refreshed = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert refreshed.status_code == 200
    token = refreshed.json()["access_token"]
    page = (await client.get("/api/me/sessions", headers=bearer(token))).json()
    assert len(page["items"]) == 1
    assert page["items"][0]["created_at"] == original_time.isoformat().replace("+00:00", "Z")
    assert page["items"][0]["last_active_at"] != page["items"][0]["created_at"]


async def test_bounded_listing_prioritises_current_and_excludes_revocations_and_expiry(
    container: Container,
    user: User,
    clock: FakeClock,
) -> None:
    current = uuid4()
    now = clock.now()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        for index in range(104):
            family = current if index == 0 else uuid4()
            await repos.refresh_tokens.add(
                RefreshToken(
                    id=uuid4(),
                    user_id=user.id,
                    token_hash=f"{index:064d}",
                    family_id=family,
                    parent_id=None,
                    issued_at=now + timedelta(seconds=index),
                    expires_at=now - timedelta(seconds=1)
                    if index == 103
                    else now + timedelta(days=1),
                    revoked_at=now if index == 102 else None,
                    ip=None,
                    user_agent=None,
                )
            )
        await repos.uow.commit()
        repository = SqlAccountSessionRepository(session)
        page = await repository.list_active(user.id, current, now)
        assert len(page.items) == 100
        assert page.truncated is True
        assert page.items[0].id == current
        await repository.revoke_others(user.id, current, now)
        await repos.uow.commit()
        page = await repository.list_active(user.id, current, now)
        assert [item.id for item in page.items] == [current]
        assert page.truncated is False


async def test_cookie_alone_cannot_manage_sessions(client: AsyncClient, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    for method, path in [
        ("GET", "/api/me/sessions"),
        ("POST", "/api/me/sessions/revoke-others"),
        ("DELETE", f"/api/me/sessions/{UUID(int=1)}"),
    ]:
        assert (await client.request(method, path)).status_code == 401


async def test_application_rechecks_original_claims_after_credential_change(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        fresh = await repos.users.lock_by_id(user.id)
        assert fresh is not None
        fresh.security_version += 1
        await repos.users.save(fresh)
        await repos.uow.commit()
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.account_sessions(session).list(claims)


async def test_selected_other_session_revocation_preserves_current(
    client: AsyncClient,
    user: User,
) -> None:
    current = await login_token(client, USER_EMAIL, USER_PASSWORD)
    other = await login_token(client, USER_EMAIL, USER_PASSWORD)
    page = (await client.get("/api/me/sessions", headers=bearer(current))).json()
    target = next(item["id"] for item in page["items"] if not item["current"])
    response = await client.delete(f"/api/me/sessions/{target}", headers=bearer(current))
    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    assert (await client.get("/api/me/sessions", headers=bearer(other))).status_code == 401
    assert (await client.get("/api/me/sessions", headers=bearer(current))).status_code == 200
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 401

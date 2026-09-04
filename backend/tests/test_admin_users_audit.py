"""User administration and the audit log."""

from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient

from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    login,
    login_token,
    restore_session,
)


async def test_list_users(client: AsyncClient, admin: User, user: User) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.get("/api/admin/users", headers=bearer(token))
    assert response.status_code == 200
    emails = {item["email"] for item in response.json()["items"]}
    assert emails == {ADMIN_EMAIL, USER_EMAIL}


async def test_role_change_ends_sessions(client: AsyncClient, admin: User, user: User) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    user_csrf = client.cookies.get("ase_csrf") or ""
    user_refresh = client.cookies.get("ase_refresh") or ""
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        f"/api/admin/users/{user.id}", json={"role": "admin"}, headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    headers = restore_session(client, user_refresh, user_csrf)
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 401


async def test_deactivation_blocks_access(client: AsyncClient, admin: User, user: User) -> None:
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        f"/api/admin/users/{user.id}", json={"is_active": False}, headers=bearer(admin_token)
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert (await client.get("/api/me", headers=bearer(user_token))).status_code == 401
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 401


async def test_no_op_update_is_fine(client: AsyncClient, admin: User, user: User) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(f"/api/admin/users/{user.id}", json={}, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["email"] == USER_EMAIL


async def test_self_modification_is_refused(client: AsyncClient, admin: User) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        f"/api/admin/users/{admin.id}", json={"is_active": False}, headers=bearer(token)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "self_modification"


async def test_unknown_user_is_404(client: AsyncClient, admin: User) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert (
        await client.patch(f"/api/admin/users/{uuid4()}", json={}, headers=bearer(token))
    ).status_code == 404
    assert (
        await client.post(f"/api/admin/users/{uuid4()}/reset-link", headers=bearer(token))
    ).status_code == 404


async def test_audit_log_pagination(client: AsyncClient, admin: User, user: User) -> None:
    for _ in range(3):
        await login(client, USER_EMAIL, USER_PASSWORD)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    first = await client.get("/api/admin/audit-log", params={"limit": 2}, headers=bearer(token))
    assert first.status_code == 200
    page = first.json()
    assert len(page["items"]) == 2
    assert page["next_before"] == page["items"][-1]["id"]
    assert page["items"][0]["action"] == "login_succeeded"
    assert page["items"][0]["actor_user_id"] == str(admin.id)
    second = await client.get(
        "/api/admin/audit-log",
        params={"limit": 50, "before": page["next_before"]},
        headers=bearer(token),
    )
    ids = [item["id"] for item in second.json()["items"]]
    assert ids and all(item_id < page["next_before"] for item_id in ids)
    assert second.json()["next_before"] is None
    assert (await client.get("/api/admin/audit-log", params={"limit": 0})).status_code == 401


async def test_non_admin_cannot_read_audit(client: AsyncClient, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.get("/api/admin/audit-log", headers=bearer(token))).status_code == 403
    assert (await client.get("/api/admin/users", headers=bearer(token))).status_code == 403

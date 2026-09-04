"""Request an account, approve it, activate with the link, log in."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_PASSWORD,
    FakeClock,
    bearer,
    create_user,
    login,
    login_token,
    token_from_link,
)

NEW_EMAIL = "newcomer@example.com"
REQUEST_BODY = {"email": NEW_EMAIL, "display_name": "New Comer", "reason": "Analyst"}
ACCEPTED_MESSAGE = "If the address is eligible, an administrator will review the request."


async def request_account(client: AsyncClient, body: dict[str, str] | None = None) -> None:
    response = await client.post("/api/auth/request-account", json=body or REQUEST_BODY)
    assert response.status_code == 202
    assert response.json() == {"message": ACCEPTED_MESSAGE}


async def pending_requests(client: AsyncClient, token: str) -> list[dict[str, object]]:
    response = await client.get("/api/admin/account-requests", headers=bearer(token))
    assert response.status_code == 200
    items: list[dict[str, object]] = response.json()["items"]
    return items


async def test_full_activation_flow(client: AsyncClient, admin: User, clock: FakeClock) -> None:
    await request_account(client)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    items = await pending_requests(client, token)
    assert len(items) == 1
    assert items[0]["email"] == NEW_EMAIL
    assert items[0]["status"] == "pending"
    approve = await client.post(
        f"/api/admin/account-requests/{items[0]['id']}/approve",
        json={"role": "user"},
        headers=bearer(token),
    )
    assert approve.status_code == 200, approve.text
    body = approve.json()
    assert body["user"]["email"] == NEW_EMAIL
    assert body["activation_link"].startswith("http://app.test/activate?token=")
    assert await pending_requests(client, token) == []
    # Nobody can log in before the password is set.
    assert (await login(client, NEW_EMAIL, USER_PASSWORD)).status_code == 401
    secret = token_from_link(body["activation_link"])
    set_password = await client.post(
        "/api/auth/set-password", json={"token": secret, "new_password": USER_PASSWORD}
    )
    assert set_password.status_code == 204
    assert (await login(client, NEW_EMAIL, USER_PASSWORD)).status_code == 200
    # The activation link is single use.
    reuse = await client.post(
        "/api/auth/set-password", json={"token": secret, "new_password": USER_PASSWORD}
    )
    assert reuse.status_code == 400
    assert reuse.json()["error"]["code"] == "invalid_token"


async def test_duplicate_requests_get_the_same_answer(client: AsyncClient, admin: User) -> None:
    await request_account(client)
    await request_account(client)
    await request_account(client, {"email": ADMIN_EMAIL, "display_name": "Impostor"})
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert len(await pending_requests(client, token)) == 1


async def test_request_account_rate_limit(client: AsyncClient) -> None:
    for _ in range(3):
        await request_account(client)
    response = await client.post("/api/auth/request-account", json=REQUEST_BODY)
    assert response.status_code == 429


async def test_request_account_validation(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/request-account", json={"email": "bad", "display_name": ""}
    )
    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) == {"email", "display_name"}


async def test_reject_and_decided_conflicts(client: AsyncClient, admin: User) -> None:
    await request_account(client)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    request_id = (await pending_requests(client, token))[0]["id"]
    reject = await client.post(
        f"/api/admin/account-requests/{request_id}/reject",
        json={"reason": "Unknown person"},
        headers=bearer(token),
    )
    assert reject.status_code == 204
    again = await client.post(
        f"/api/admin/account-requests/{request_id}/reject", json={}, headers=bearer(token)
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "already_decided"
    approve = await client.post(
        f"/api/admin/account-requests/{request_id}/approve", json={}, headers=bearer(token)
    )
    assert approve.status_code == 409
    rejected = await client.get(
        "/api/admin/account-requests", params={"status": "rejected"}, headers=bearer(token)
    )
    assert rejected.json()["items"][0]["status"] == "rejected"


async def test_unknown_request_is_404(client: AsyncClient, admin: User) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.post(
        f"/api/admin/account-requests/{uuid4()}/approve", json={}, headers=bearer(token)
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_approve_when_email_already_taken(
    client: AsyncClient, admin: User, container: Container
) -> None:
    await request_account(client)
    await create_user(container, email=NEW_EMAIL, password=USER_PASSWORD)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    request_id = (await pending_requests(client, token))[0]["id"]
    response = await client.post(
        f"/api/admin/account-requests/{request_id}/approve", json={}, headers=bearer(token)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_activation_link_expires(client: AsyncClient, admin: User, clock: FakeClock) -> None:
    await request_account(client)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    request_id = (await pending_requests(client, token))[0]["id"]
    approve = await client.post(
        f"/api/admin/account-requests/{request_id}/approve", json={}, headers=bearer(token)
    )
    secret = token_from_link(approve.json()["activation_link"])
    clock.advance(timedelta(days=8))
    response = await client.post(
        "/api/auth/set-password", json={"token": secret, "new_password": USER_PASSWORD}
    )
    assert response.status_code == 400


async def test_weak_password_is_explained(client: AsyncClient, admin: User) -> None:
    await request_account(client)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    request_id = (await pending_requests(client, token))[0]["id"]
    approve = await client.post(
        f"/api/admin/account-requests/{request_id}/approve", json={}, headers=bearer(token)
    )
    secret = token_from_link(approve.json()["activation_link"])
    response = await client.post(
        "/api/auth/set-password", json={"token": secret, "new_password": "password1234"}
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "weak_password"
    assert body["fields"]["new_password"] == "This password is too common."


async def test_admin_routes_need_admin(client: AsyncClient, user: User) -> None:
    token = await login_token(client, "user@example.com", USER_PASSWORD)
    response = await client.get("/api/admin/account-requests", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert (await client.get("/api/admin/account-requests")).status_code == 401

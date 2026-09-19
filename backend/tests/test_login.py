"""Login: success, generic failures, lockout and rate limits."""

from __future__ import annotations

from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.users import Role, User
from helpers import (
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    create_user,
    login,
    set_cookie_headers,
)


async def test_login_returns_token_and_cookies(client: AsyncClient, user: User) -> None:
    response = await login(client, USER_EMAIL, USER_PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert body["user"]["email"] == USER_EMAIL
    assert body["user"]["role"] == "user"
    assert "password_hash" not in body["user"]
    cookies = set_cookie_headers(response)
    refresh = next(c for c in cookies if c.startswith("ase_refresh="))
    csrf = next(c for c in cookies if c.startswith("ase_csrf="))
    assert "HttpOnly" in refresh
    assert "Path=/api/auth" in refresh
    assert "SameSite=strict" in refresh
    assert "HttpOnly" not in csrf
    assert "Path=/" in csrf
    assert client.cookies.get("ase_refresh") is not None


async def test_email_is_case_insensitive(client: AsyncClient, user: User) -> None:
    response = await login(client, USER_EMAIL.upper(), USER_PASSWORD)
    assert response.status_code == 200


async def test_failures_are_indistinguishable(client: AsyncClient, user: User) -> None:
    wrong = await login(client, USER_EMAIL, "not-the-password-at-all")
    unknown = await login(client, "nobody@example.com", USER_PASSWORD)
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert not set_cookie_headers(wrong)


async def test_inactive_and_passwordless_users_cannot_log_in(
    client: AsyncClient, container: Container
) -> None:
    await create_user(container, email="off@example.com", password=USER_PASSWORD, is_active=False)
    await create_user(container, email="pending@example.com", password=None)
    assert (await login(client, "off@example.com", USER_PASSWORD)).status_code == 401
    assert (await login(client, "pending@example.com", USER_PASSWORD)).status_code == 401


async def test_repeated_failures_do_not_create_account_lockout(
    client: AsyncClient, user: User, clock: FakeClock, container: Container
) -> None:
    # Spaced beyond the request-rate window to exercise persistent account state.
    for _ in range(4):
        assert (await login(client, USER_EMAIL, "wrong-password-value")).status_code == 401
        clock.advance(timedelta(seconds=61))
    # The right password works after the request-rate window. Attackers cannot lock the account.
    assert (await login(client, USER_EMAIL, "wrong-password-value")).status_code == 401
    clock.advance(timedelta(seconds=61))
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 50)
    actions = [entry.action for entry in entries]
    assert AuditAction.ACCOUNT_LOCKED not in actions
    assert AuditAction.LOGIN_SUCCEEDED in actions


async def test_failure_window_resets(client: AsyncClient, user: User, clock: FakeClock) -> None:
    for _ in range(4):
        await login(client, USER_EMAIL, "wrong-password-value")
    clock.advance(timedelta(minutes=16))
    # Old failures no longer count, so one more failure does not lock the account.
    await login(client, USER_EMAIL, "wrong-password-value")
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200


async def test_rate_limit_per_ip(client: AsyncClient, clock: FakeClock) -> None:
    for index in range(10):
        response = await login(client, f"person{index}@example.com", "irrelevant-password")
        assert response.status_code == 401
    limited = await login(client, "person11@example.com", "irrelevant-password")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1
    clock.advance(timedelta(seconds=61))
    assert (await login(client, "person12@example.com", "irrelevant-password")).status_code == 401


async def test_rate_limit_per_email(client: AsyncClient, user: User) -> None:
    for _ in range(5):
        assert (await login(client, USER_EMAIL, "wrong-password-value")).status_code == 401
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 429


async def test_admin_role_is_reported(client: AsyncClient, container: Container) -> None:
    await create_user(container, email="boss@example.com", password=USER_PASSWORD, role=Role.ADMIN)
    response = await login(client, "boss@example.com", USER_PASSWORD)
    assert response.json()["user"]["role"] == "admin"

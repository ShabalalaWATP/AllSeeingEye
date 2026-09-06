"""Self-service password changes require current proofs and invalidate old credentials."""

from dataclasses import replace
from datetime import timedelta

import pyotp
import pytest
from httpx import AsyncClient

from ase.api.account_schemas import ChangePasswordIn
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.tokens import TokenPurpose
from ase.domain.users import Role, User
from helpers import (
    ADMIN_PASSWORD,
    USER_PASSWORD,
    FakeClock,
    bearer,
    create_user,
    login,
    login_token,
    restore_session,
)
from password_change_helpers import NEW_PASSWORD, outstanding_link
from totp_helpers import enable_totp


@pytest.mark.parametrize("role", [Role.USER, Role.MANAGER, Role.ADMIN])
async def test_every_account_role_can_change_own_password(
    client: AsyncClient,
    container: Container,
    role: Role,
) -> None:
    actor = await create_user(
        container, email="self-service@example.com", password=USER_PASSWORD, role=role
    )
    token = await login_token(client, actor.email, USER_PASSWORD)
    changed = await client.post(
        "/api/me/password",
        headers=bearer(token),
        json={
            "current_password": USER_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )
    assert changed.status_code == 204 and not changed.content
    assert changed.headers["cache-control"] == "no-store"
    assert client.cookies.get("ase_refresh") is None and client.cookies.get("ase_csrf") is None
    current = await login(client, actor.email, NEW_PASSWORD)
    assert current.status_code == 200 and current.json()["user"]["role"] == role.value


async def test_change_ends_all_old_sessions_and_outstanding_password_links(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    first = await login_token(client, user.email, USER_PASSWORD)
    second = await login_token(client, user.email, USER_PASSWORD)
    old_refresh = client.cookies.get("ase_refresh") or ""
    old_csrf = client.cookies.get("ase_csrf") or ""
    links = [await outstanding_link(container, user, purpose) for purpose in TokenPurpose]
    changed = await client.post(
        "/api/me/password",
        headers=bearer(second),
        json={
            "current_password": USER_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )
    assert changed.status_code == 204
    for token in (first, second):
        assert (await client.get("/api/me", headers=bearer(token))).status_code == 401
    headers = restore_session(client, old_refresh, old_csrf)
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 401
    for secret in links:
        reset = await client.post(
            "/api/auth/set-password",
            json={
                "token": secret,
                "new_password": "An-Older-Compromised-Password-2026",
            },
        )
        assert reset.status_code == 400
    assert (await login(client, user.email, USER_PASSWORD)).status_code == 401
    assert (await login(client, user.email, NEW_PASSWORD)).status_code == 200
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.users.get_by_id(user.id)
        entries = await repos.audit.list_before(None, 50)
        assert current and current.security_version == user.security_version + 1
        changed_entries = [
            entry for entry in entries if entry.action is AuditAction.PASSWORD_CHANGED
        ]
        assert len(changed_entries) == 1 and changed_entries[0].actor_user_id == user.id
        audit = repr(entries)
        assert not any(
            secret in audit
            for secret in [first, second, old_refresh, *links, USER_PASSWORD, NEW_PASSWORD]
        )


async def test_wrong_current_password_and_weak_new_password_preserve_session(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    wrong = await client.post(
        "/api/me/password",
        headers=bearer(token),
        json={
            "current_password": "Incorrect-Current-Password",
            "new_password": NEW_PASSWORD,
        },
    )
    assert wrong.status_code == 422 and wrong.json()["error"]["code"] == "invalid_request"
    weak = await client.post(
        "/api/me/password",
        headers=bearer(token),
        json={
            "current_password": USER_PASSWORD,
            "new_password": "password1234",
        },
    )
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "weak_password"
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 200
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 20)
        assert any(entry.action is AuditAction.PASSWORD_CHANGE_FAILED for entry in entries)
        assert "Incorrect-Current-Password" not in repr(entries)


async def test_change_requires_bearer_and_forbids_target_account_fields(
    client: AsyncClient,
    user: User,
    admin: User,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    body = {"current_password": USER_PASSWORD, "new_password": NEW_PASSWORD}
    # The refresh/CSRF cookies set by login alone cannot authorise a credential change.
    assert (await client.post("/api/me/password", json=body)).status_code == 401
    for extra in ({"user_id": str(admin.id)}, {"role": "admin"}, {"email": admin.email}):
        response = await client.post(
            "/api/me/password", headers=bearer(token), json={**body, **extra}
        )
        assert response.status_code == 422
    assert (await login(client, admin.email, ADMIN_PASSWORD)).status_code == 200


async def test_password_change_rate_budget_is_bounded(
    client: AsyncClient,
    user: User,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    for _ in range(5):
        response = await client.post(
            "/api/me/password",
            headers=bearer(token),
            json={
                "current_password": "Wrong-Current-Password",
                "new_password": NEW_PASSWORD,
            },
        )
        assert response.status_code == 422
    limited = await client.post(
        "/api/me/password",
        headers=bearer(token),
        json={
            "current_password": USER_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )
    assert limited.status_code == 429 and "retry-after" in limited.headers
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 200


async def test_inactive_or_stale_session_cannot_change_password(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.users.save(replace(user, is_active=False, security_version=1))
        await session.commit()
    response = await client.post(
        "/api/me/password",
        headers=bearer(token),
        json={
            "current_password": USER_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )
    assert response.status_code == 401


async def test_enrolled_factor_is_required_and_preserved(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    headers, secret = await enable_totp(client, clock)
    body = {"current_password": ADMIN_PASSWORD, "new_password": NEW_PASSWORD}
    # This valid-looking code was already consumed by the login helper.
    for code in (
        None,
        pyotp.TOTP(secret).at(clock.now()),
        pyotp.TOTP(secret).at(clock.now() - timedelta(minutes=3)),
    ):
        response = await client.post(
            "/api/me/password", headers=headers, json={**body, "totp_code": code}
        )
        assert response.status_code == 422
    clock.advance(timedelta(minutes=1))
    code = pyotp.TOTP(secret).at(clock.now())
    success = await client.post(
        "/api/me/password", headers=headers, json={**body, "totp_code": code}
    )
    assert success.status_code == 204
    assert (await login(client, admin.email, NEW_PASSWORD)).status_code == 401
    # Neither the previous code nor the password change disabled the second factor.
    reused = await client.post(
        "/api/auth/login",
        json={
            "email": admin.email,
            "password": NEW_PASSWORD,
            "totp_code": code,
        },
    )
    assert reused.status_code == 401
    clock.advance(timedelta(minutes=1))
    signed_in = await client.post(
        "/api/auth/login",
        json={
            "email": admin.email,
            "password": NEW_PASSWORD,
            "totp_code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert signed_in.status_code == 200


def test_credentials_are_not_exposed_in_input_model_representation() -> None:
    body = ChangePasswordIn(
        current_password=USER_PASSWORD, new_password=NEW_PASSWORD, totp_code="654321"
    )
    assert not any(value in repr(body) for value in (USER_PASSWORD, NEW_PASSWORD, "654321"))

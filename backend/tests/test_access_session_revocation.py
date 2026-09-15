"""Access tokens are tied to an active family and the current credential version."""

from datetime import timedelta
from uuid import uuid4

import jwt
import pyotp
import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import Role, User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    create_user,
    csrf_headers,
    login_token,
    password_login,
    token_from_link,
)
from totp_helpers import enable_totp, verify_code


async def test_logout_ends_only_current_family_including_rotated_access(
    client: AsyncClient,
    user: User,
) -> None:
    first = await login_token(client, USER_EMAIL, USER_PASSWORD)
    second = await login_token(client, USER_EMAIL, USER_PASSWORD)
    rotated = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    third = rotated.json()["access_token"]
    assert (await client.get("/api/me", headers=bearer(second))).status_code == 200
    assert (await client.post("/api/auth/logout", headers=csrf_headers(client))).status_code == 204
    for token in (second, third):
        assert (await client.get("/api/me", headers=bearer(token))).status_code == 401
    assert (await client.get("/api/me", headers=bearer(first))).status_code == 200


async def test_password_reset_ends_all_access_and_refresh_sessions(
    client: AsyncClient,
    admin: User,
    user: User,
) -> None:
    first = await login_token(client, USER_EMAIL, USER_PASSWORD)
    second = await login_token(client, USER_EMAIL, USER_PASSWORD)
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    issued = await client.post(
        f"/api/admin/users/{user.id}/reset-link", headers=bearer(admin_token)
    )
    changed = await client.post(
        "/api/auth/set-password",
        json={
            "token": token_from_link(issued.json()["reset_link"]),
            "new_password": "Different-Observatory-Password-42",
        },
    )
    assert changed.status_code == 204
    for token in (first, second):
        assert (await client.get("/api/me", headers=bearer(token))).status_code == 401
    assert (await client.get("/api/me", headers=bearer(admin_token))).status_code == 200


@pytest.mark.parametrize("change", [{"role": "admin"}, {"is_active": False}])
async def test_role_and_active_changes_end_access_immediately(
    client: AsyncClient,
    admin: User,
    user: User,
    change: dict[str, object],
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    administrator = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert (
        await client.patch(
            f"/api/admin/users/{user.id}", json=change, headers=bearer(administrator)
        )
    ).status_code == 200
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 401
    if change.get("role") == "admin":
        promoted = await login_token(client, USER_EMAIL, USER_PASSWORD)
        assert (await client.get("/api/me", headers=bearer(promoted))).json()["role"] == "admin"


@pytest.mark.parametrize(
    "mutations",
    [
        {"sid": None},
        {"sv": None},
        {"sv": True},
        {"sv": -1},
        {"sv": "0"},
        {"sid": "invalid"},
        {"sid": str(uuid4())},
        {"sv": 1},
    ],
)
async def test_legacy_or_invalid_session_claims_fail_closed(
    client: AsyncClient,
    container: Container,
    user: User,
    mutations: dict[str, object],
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    claims = jwt.decode(token, options={"verify_signature": False})
    for key, value in mutations.items():
        if value is None:
            claims.pop(key)
        else:
            claims[key] = value
    changed = jwt.encode(claims, container.settings.jwt_secret_value, algorithm="HS256")
    assert (await client.get("/api/me", headers=bearer(changed))).status_code == 401


async def test_demoted_account_keeps_enrolled_factor(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    old_headers, secret = await enable_totp(client, clock)
    other = await create_user(
        container, email="other-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    token = await login_token(client, other.email, ADMIN_PASSWORD)
    assert (
        await client.patch(
            f"/api/admin/users/{admin.id}", json={"role": "user"}, headers=bearer(token)
        )
    ).status_code == 200
    assert (await client.get("/api/me", headers=old_headers)).status_code == 401
    clock.advance(timedelta(minutes=1))
    pending = await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert pending.status_code == 200
    assert pending.json()["mfa_required"]
    assert pending.json()["methods"] == ["authenticator"]
    assert not pending.json()["enrollment_required"]
    assert "access_token" not in pending.json()
    signed_in = await verify_code(
        client, pending.json()["challenge_token"], pyotp.TOTP(secret).at(clock.now())
    )
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["role"] == "user"


async def test_local_totp_recovery_ends_existing_access(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    headers, _ = await enable_totp(client, clock)
    async with container.session_factory() as session:
        current = await container.repositories(session).users.get_by_id(admin.id)
        assert current
        await container.totp(session).recover_local(current, ADMIN_PASSWORD)
    assert (await client.get("/api/me", headers=headers)).status_code == 401
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 401
    pending = await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert pending.status_code == 200
    assert pending.json()["mfa_required"] and pending.json()["enrollment_required"]
    assert "access_token" not in pending.json()

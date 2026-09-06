"""Access tokens: bearer handling, expiry, tampering."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import jwt
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token


async def test_me_returns_the_user(client: AsyncClient, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/me", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == USER_EMAIL
    assert body["id"] == str(user.id)
    assert body["last_login_at"] is not None


async def test_missing_or_malformed_tokens(client: AsyncClient) -> None:
    assert (await client.get("/api/me")).status_code == 401
    assert (await client.get("/api/me", headers={"Authorization": "Basic abc"})).status_code == 401
    garbage = await client.get("/api/me", headers=bearer("not.a.jwt"))
    assert garbage.status_code == 401
    assert garbage.json()["error"]["code"] == "unauthenticated"


async def test_expired_access_token(client: AsyncClient, user: User, clock: FakeClock) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    clock.advance(timedelta(minutes=16))
    response = await client.get("/api/me", headers=bearer(token))
    assert response.status_code == 401


async def test_tokens_signed_with_another_key_or_type_fail(
    client: AsyncClient, user: User, container: Container
) -> None:
    now = int(container.clock.now().timestamp())
    claims = {
        "sub": str(user.id),
        "role": "user",
        "typ": "access",
        "iat": now,
        "exp": now + 600,
        "jti": "x",
        "sid": str(uuid4()),
        "sv": 0,
    }
    forged = jwt.encode(claims, "another-secret-that-is-long-enough-for-hmac", algorithm="HS256")
    assert (await client.get("/api/me", headers=bearer(forged))).status_code == 401
    wrong_type = jwt.encode(
        {**claims, "typ": "refresh"}, container.settings.jwt_secret_value, algorithm="HS256"
    )
    assert (await client.get("/api/me", headers=bearer(wrong_type))).status_code == 401
    bad_subject = jwt.encode(
        {**claims, "sub": "not-a-uuid"}, container.settings.jwt_secret_value, algorithm="HS256"
    )
    assert (await client.get("/api/me", headers=bearer(bad_subject))).status_code == 401
    unknown_user = jwt.encode(
        {**claims, "sub": "00000000-0000-0000-0000-000000000000"},
        container.settings.jwt_secret_value,
        algorithm="HS256",
    )
    assert (await client.get("/api/me", headers=bearer(unknown_user))).status_code == 401

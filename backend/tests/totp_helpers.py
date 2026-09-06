"""Fixture-only TOTP setup shared by authentication regression tests."""

from datetime import timedelta

import pyotp
from httpx import AsyncClient, Response

from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    login_token,
    password_login,
)


async def start_enrolment(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.post(
        "/api/auth/totp/enrol",
        headers=headers,
        json={"password": USER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return headers, response.json()["secret"]


async def enable_totp(client: AsyncClient, clock: FakeClock) -> tuple[dict[str, str], str]:
    pending = await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert pending.status_code == 200, pending.text
    assert pending.json()["enrollment_required"]
    challenge = pending.json()["challenge_token"]
    enrolment = await client.post("/api/auth/mfa/enrol-app", json={"challenge_token": challenge})
    assert enrolment.status_code == 200, enrolment.text
    secret = enrolment.json()["secret"]
    response = await verify_code(client, challenge, pyotp.TOTP(secret).at(clock.now()))
    assert response.status_code == 200, response.text
    clock.advance(timedelta(seconds=30))
    signed_in = await totp_login(
        client, ADMIN_EMAIL, ADMIN_PASSWORD, pyotp.TOTP(secret).at(clock.now())
    )
    assert signed_in.status_code == 200, signed_in.text
    return bearer(signed_in.json()["access_token"]), secret


async def verify_code(client: AsyncClient, challenge: str, code: str) -> Response:
    return await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": challenge,
            "method": "authenticator",
            "code": code,
        },
    )


async def totp_login(client: AsyncClient, email: str, password: str, code: str) -> Response:
    pending = await password_login(client, email, password)
    assert pending.status_code == 200, pending.text
    assert pending.json()["mfa_required"]
    assert "access_token" not in pending.json()
    return await verify_code(client, pending.json()["challenge_token"], code)

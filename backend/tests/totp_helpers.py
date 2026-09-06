"""Fixture-only TOTP setup shared by authentication regression tests."""

from datetime import timedelta

import pyotp
from httpx import AsyncClient

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, FakeClock, bearer, login_token


async def start_enrolment(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.post(
        "/api/auth/totp/enrol",
        headers=headers,
        json={"password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return headers, response.json()["secret"]


async def enable_totp(client: AsyncClient, clock: FakeClock) -> tuple[dict[str, str], str]:
    headers, secret = await start_enrolment(client)
    response = await client.post(
        "/api/auth/totp/confirm",
        headers=headers,
        json={"code": pyotp.TOTP(secret).at(clock.now())},
    )
    assert response.status_code == 204, response.text
    assert (await client.get("/api/me", headers=headers)).status_code == 401
    clock.advance(timedelta(seconds=30))
    signed_in = await client.post(
        "/api/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "totp_code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert signed_in.status_code == 200, signed_in.text
    return bearer(signed_in.json()["access_token"]), secret

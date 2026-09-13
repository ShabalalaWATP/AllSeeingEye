"""Forgotten passwords, admin-issued reset links and session revocation on password change."""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient

from ase.domain.tokens import TokenPurpose
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    RecordingEmailSender,
    bearer,
    login,
    login_token,
    restore_session,
    token_from_link,
)

FORGOT_MESSAGE = (
    "If the address is registered, check your email for a reset link. "
    "You can request another if it does not arrive."
)
NEW_PASSWORD = "Harbour-Lights-Fade-77"


async def test_forgot_password_never_reveals_accounts(
    client: AsyncClient, user: User, email_sender: RecordingEmailSender
) -> None:
    known = await client.post("/api/auth/forgot-password", json={"email": USER_EMAIL})
    unknown = await client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json() == {"message": FORGOT_MESSAGE}
    # Without email transport nothing is delivered, but a token was still minted for the user.
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0][1] is TokenPurpose.RESET


async def test_forgot_password_rate_limit(client: AsyncClient) -> None:
    for _ in range(3):
        await client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    response = await client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    assert response.status_code == 429


async def test_admin_reset_link_changes_password_and_ends_sessions(
    client: AsyncClient, admin: User, user: User
) -> None:
    await login(client, USER_EMAIL, USER_PASSWORD)
    user_csrf = client.cookies.get("ase_csrf") or ""
    user_refresh = client.cookies.get("ase_refresh") or ""
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    issued = await client.post(f"/api/admin/users/{user.id}/reset-link", headers=bearer(token))
    assert issued.status_code == 200
    link = issued.json()["reset_link"]
    assert link.startswith("http://app.test/reset-password?token=")
    response = await client.post(
        "/api/auth/set-password",
        json={"token": token_from_link(link), "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 204
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 401
    assert (await login(client, USER_EMAIL, NEW_PASSWORD)).status_code == 200
    headers = restore_session(client, user_refresh, user_csrf)
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 401


async def test_reset_link_expires(
    client: AsyncClient, admin: User, user: User, clock: FakeClock
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    issued = await client.post(f"/api/admin/users/{user.id}/reset-link", headers=bearer(token))
    clock.advance(timedelta(minutes=31))
    response = await client.post(
        "/api/auth/set-password",
        json={"token": token_from_link(issued.json()["reset_link"]), "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400


async def test_set_password_rate_limit(client: AsyncClient) -> None:
    for _ in range(10):
        response = await client.post(
            "/api/auth/set-password", json={"token": "nonsense", "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 400
    response = await client.post(
        "/api/auth/set-password", json={"token": "nonsense", "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 429


class TestWithEmailDelivery:
    @pytest.fixture
    def email_sender(self) -> RecordingEmailSender:
        return RecordingEmailSender(delivered=True)

    async def test_delivered_link_resets_password(
        self, client: AsyncClient, user: User, email_sender: RecordingEmailSender
    ) -> None:
        await client.post("/api/auth/forgot-password", json={"email": USER_EMAIL})
        _, purpose, link = email_sender.sent[0]
        assert purpose is TokenPurpose.RESET
        response = await client.post(
            "/api/auth/set-password",
            json={"token": token_from_link(link), "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 204
        assert (await login(client, USER_EMAIL, NEW_PASSWORD)).status_code == 200

    async def test_delivered_activation_hides_the_link(
        self, client: AsyncClient, admin: User, email_sender: RecordingEmailSender
    ) -> None:
        await client.post(
            "/api/auth/request-account",
            json={"email": "fresh@example.com", "display_name": "Fresh"},
        )
        token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        listed = await client.get("/api/admin/account-requests", headers=bearer(token))
        request_id = listed.json()["items"][0]["id"]
        approve = await client.post(
            f"/api/admin/account-requests/{request_id}/approve", json={}, headers=bearer(token)
        )
        assert approve.status_code == 200
        assert approve.json()["activation_link"] is None
        assert email_sender.sent[-1][1] is TokenPurpose.ACTIVATION

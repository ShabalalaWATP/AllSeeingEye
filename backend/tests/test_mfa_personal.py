"""Personal MFA setup, removal and password changes require scoped one-use proofs."""

from datetime import timedelta

from httpx import AsyncClient

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.container import Container
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    RecordingEmailSender,
    bearer,
    login_token,
)


async def enrol_email(
    client: AsyncClient, mail: RecordingEmailSender, headers: dict[str, str], password: str
) -> dict:
    mail.delivered = True
    pending = await client.post(
        "/api/auth/mfa/email/enrol", headers=headers, json={"password": password}
    )
    assert pending.status_code == 200, pending.text
    return {"challenge_token": pending.json()["challenge_token"], "code": mail.codes[-1][1]}


async def test_user_can_enable_email_then_disable_with_fresh_proof(
    client: AsyncClient, user: User, email_sender: RecordingEmailSender
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    ).status_code == 204
    assert (await client.get("/api/me", headers=headers)).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    status = await client.get("/api/auth/mfa", headers=headers)
    assert status.json()["methods"] == ["email"]
    assert status.json()["required"] is False
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    ).status_code == 422
    pending = await client.post(
        "/api/auth/mfa/email/disable", headers=headers, json={"password": USER_PASSWORD}
    )
    assert pending.status_code == 200, pending.text
    removed = await client.post(
        "/api/auth/mfa/email/disable/confirm",
        headers=headers,
        json={
            "challenge_token": pending.json()["challenge_token"],
            "code": email_sender.codes[-1][1],
        },
    )
    assert removed.status_code == 204, removed.text
    response = await client.post(
        "/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD}
    )
    assert "access_token" in response.json()


async def test_email_enrolment_token_cannot_be_used_for_login(
    client: AsyncClient, user: User, email_sender: RecordingEmailSender
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    response = await client.post("/api/auth/mfa/verify", json={**body, "method": "email"})
    assert response.status_code == 401
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    ).status_code == 204


async def test_email_enabled_password_change_needs_email_proof(
    client: AsyncClient, user: User, email_sender: RecordingEmailSender
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    ).status_code == 204
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    payload = {"current_password": USER_PASSWORD, "new_password": "Different-Long-Password-2026"}
    assert (await client.post("/api/me/password", headers=headers, json=payload)).status_code == 422
    pending = await client.post(
        "/api/auth/mfa/password-change", headers=headers, json={"password": USER_PASSWORD}
    )
    assert pending.status_code == 200, pending.text
    payload.update(
        mfa_challenge_token=pending.json()["challenge_token"], mfa_code=email_sender.codes[-1][1]
    )
    assert (await client.post("/api/me/password", headers=headers, json=payload)).status_code == 204
    assert (await client.get("/api/me", headers=headers)).status_code == 401
    response = await client.post(
        "/api/auth/login", json={"email": USER_EMAIL, "password": payload["new_password"]}
    )
    assert response.json()["mfa_required"]


async def test_admin_cannot_remove_last_authenticator(client: AsyncClient, admin: User) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={"password": ADMIN_PASSWORD, "code": "123456"},
    )
    assert response.status_code == 422
    assert "at least one MFA" in response.text


async def test_login_challenge_cannot_authorise_factor_or_password_changes(
    client: AsyncClient,
    user: User,
    email_sender: RecordingEmailSender,
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    ).status_code == 204
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    pending = await client.post(
        "/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD}
    )
    proof = {
        "challenge_token": pending.json()["challenge_token"],
        "code": email_sender.codes[-1][1],
    }
    result = await client.post("/api/auth/mfa/email/disable/confirm", headers=headers, json=proof)
    assert result.status_code == 422
    result = await client.post(
        "/api/me/password",
        headers=headers,
        json={
            "current_password": USER_PASSWORD,
            "new_password": "Different-Long-Password-2026",
            "mfa_challenge_token": proof["challenge_token"],
            "mfa_code": proof["code"],
        },
    )
    assert result.status_code == 422
    result = await client.post("/api/auth/mfa/verify", json={**proof, "method": "email"})
    assert result.status_code == 200


async def test_personal_wrong_password_or_code_keeps_session_and_counts_once(
    client: AsyncClient,
    user: User,
    email_sender: RecordingEmailSender,
    container: Container,
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    wrong = await client.post(
        "/api/auth/mfa/email/enrol", headers=headers, json={"password": "incorrect-password"}
    )
    assert wrong.status_code == 422
    assert (await client.get("/api/me", headers=headers)).status_code == 200
    body = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    wrong_code = f"{(int(body['code']) + 1) % 1_000_000:06d}"
    wrong = await client.post(
        "/api/auth/mfa/email/enrol/confirm", headers=headers, json={**body, "code": wrong_code}
    )
    assert wrong.status_code == 422
    assert (await client.get("/api/me", headers=headers)).status_code == 200
    async with container.session_factory() as session:
        challenge = await SqlMfaRepository(session).get(
            container.generator.hash(body["challenge_token"])
        )
        assert challenge and challenge.attempts == 1
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    ).status_code == 204


async def test_expired_personal_code_keeps_session_but_expired_session_is_401(
    client: AsyncClient,
    user: User,
    email_sender: RecordingEmailSender,
    clock: FakeClock,
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    body = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    clock.advance(timedelta(minutes=11))
    expired = await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    assert expired.status_code == 422
    assert (await client.get("/api/me", headers=headers)).status_code == 200
    clock.advance(timedelta(minutes=5))
    expired = await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=body)
    assert expired.status_code == 401

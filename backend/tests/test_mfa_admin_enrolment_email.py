"""A phished password cannot bind an administrator's first authenticator when email works."""

from datetime import timedelta
from typing import Any

import pyotp
from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.security.cipher import FernetCipher
from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, FakeClock, RecordingEmailSender

ENROL = "/api/auth/mfa/enrol-app"


async def _pending(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    pending: dict[str, Any] = response.json()
    assert pending["enrollment_required"] and "access_token" not in pending
    return pending


async def _send(client: AsyncClient, token: str, sender: RecordingEmailSender) -> str:
    sent = await client.post("/api/auth/mfa/email", json={"challenge_token": token})
    assert sent.status_code == 200, sent.text
    assert sender.codes[-1][0] == ADMIN_EMAIL
    return sender.codes[-1][1]


def _other(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


async def test_first_authenticator_needs_an_emailed_code_when_email_is_configured(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
    container: Container,
    email_sender: RecordingEmailSender,
) -> None:
    email_sender.delivered = True
    pending = await _pending(client)
    token = pending["challenge_token"]
    assert pending["methods"] == ["authenticator", "email"]
    assert pending["authenticator_email_proof"] is True

    # The password alone, or a guess before any code was sent, binds nothing.
    for body in ({}, {"email_code": "123456"}):
        refused = await client.post(ENROL, json={"challenge_token": token, **body})
        assert refused.status_code == 401, refused.text
        assert "secret" not in refused.text
    code = await _send(client, token, email_sender)
    wrong = await client.post(ENROL, json={"challenge_token": token, "email_code": _other(code)})
    assert wrong.status_code == 401

    enrolment = await client.post(ENROL, json={"challenge_token": token, "email_code": code})
    assert enrolment.status_code == 200, enrolment.text
    secret = enrolment.json()["secret"]

    verified = await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": token,
            "method": "authenticator",
            "code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["user"]["role"] == "admin"
    async with container.session_factory() as session:
        assert not await SqlMfaRepository(session).email_enabled(admin.id)
        reasons = [
            (row.details or {}).get("reason")
            for row in await session.scalars(
                select(AuditLogRow).where(AuditLogRow.actor_user_id == admin.id)
            )
        ]
    # Guessed codes (unsent and wrong) are audited failures; a missing code is not a guess.
    assert reasons.count("invalid_second_factor") == 2


async def test_emailed_proof_expires_and_wrong_codes_exhaust_the_challenge(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
    email_sender: RecordingEmailSender,
) -> None:
    email_sender.delivered = True
    token = (await _pending(client))["challenge_token"]
    code = await _send(client, token, email_sender)
    clock.advance(timedelta(minutes=5, seconds=1))
    expired = await client.post(ENROL, json={"challenge_token": token, "email_code": code})
    assert expired.status_code == 401

    fresh = await _send(client, token, email_sender)
    for _ in range(4):
        wrong = await client.post(
            ENROL, json={"challenge_token": token, "email_code": _other(fresh)}
        )
        assert wrong.status_code == 401
    # Five failed proofs end the challenge, even for the right code.
    late = await client.post(ENROL, json={"challenge_token": token, "email_code": fresh})
    assert late.status_code in (401, 429)
    # A new password challenge still lets the administrator enrol: no permanent lockout.
    retry = (await _pending(client))["challenge_token"]
    code = await _send(client, retry, email_sender)
    enrolled = await client.post(ENROL, json={"challenge_token": retry, "email_code": code})
    assert enrolled.status_code == 200, enrolled.text


async def test_a_proved_challenge_refreshes_its_key_but_spends_the_email_code(
    client: AsyncClient, admin: User, email_sender: RecordingEmailSender
) -> None:
    email_sender.delivered = True
    token = (await _pending(client))["challenge_token"]
    code = await _send(client, token, email_sender)
    first = await client.post(ENROL, json={"challenge_token": token, "email_code": code})
    assert first.status_code == 200, first.text
    # The pending setup key can be replaced without another email.
    again = await client.post(ENROL, json={"challenge_token": token})
    assert again.status_code == 200, again.text
    assert again.json()["secret"] != first.json()["secret"]
    # The spent email code cannot also enable email MFA.
    reused = await client.post(
        "/api/auth/mfa/verify", json={"challenge_token": token, "method": "email", "code": code}
    )
    assert reused.status_code == 401


async def test_without_email_delivery_the_documented_password_only_enrolment_remains(
    client: AsyncClient, admin: User, email_sender: RecordingEmailSender
) -> None:
    assert email_sender.available is False
    pending = await _pending(client)
    assert pending["methods"] == ["authenticator"]
    assert pending["authenticator_email_proof"] is False
    enrolment = await client.post(ENROL, json={"challenge_token": pending["challenge_token"]})
    assert enrolment.status_code == 200, enrolment.text


async def test_email_only_installations_do_not_ask_for_an_authenticator_proof(
    client: AsyncClient,
    admin: User,
    container: Container,
    email_sender: RecordingEmailSender,
) -> None:
    email_sender.delivered = True
    container.cipher = FernetCipher(None)
    pending = await _pending(client)
    assert pending["methods"] == ["email"]
    assert pending["authenticator_email_proof"] is False


async def test_enrolment_code_must_be_six_digits(client: AsyncClient, admin: User) -> None:
    token = (await _pending(client))["challenge_token"]
    malformed = await client.post(ENROL, json={"challenge_token": token, "email_code": "12ab56"})
    assert malformed.status_code == 422
    assert "12ab56" not in malformed.text

"""Password challenges grant no access until a single-use second factor succeeds."""

from datetime import timedelta

import pyotp
import pytest
from httpx import AsyncClient

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.security.cipher import FernetCipher
from ase.container import Container
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    RecordingEmailSender,
)


async def pending_admin(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    assert "access_token" not in response.json()
    return response.json()


async def test_admin_password_only_is_restricted_until_enrolled(
    client: AsyncClient, admin: User, clock: FakeClock
) -> None:
    pending = await pending_admin(client)
    assert pending["mfa_required"] and pending["enrollment_required"]
    token = pending["challenge_token"]
    assert (
        await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401
    enrol = await client.post("/api/auth/mfa/enrol-app", json={"challenge_token": token})
    assert enrol.status_code == 200, enrol.text
    verified = await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": token,
            "method": "authenticator",
            "code": pyotp.TOTP(enrol.json()["secret"]).at(clock.now()),
        },
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["user"]["role"] == "admin"
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    assert (await client.get("/api/admin/users", headers=headers)).status_code == 200
    assert (
        await client.post(
            "/api/auth/mfa/verify",
            json={
                "challenge_token": token,
                "method": "authenticator",
                "code": pyotp.TOTP(enrol.json()["secret"]).at(clock.now()),
            },
        )
    ).status_code == 401


async def test_user_without_factor_gets_normal_session(client: AsyncClient, user: User) -> None:
    result = await client.post(
        "/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD}
    )
    assert result.status_code == 200
    assert "access_token" in result.json()


async def test_admin_without_available_enrolment_method_gets_configuration_error(
    client: AsyncClient,
    admin: User,
    container: Container,
) -> None:
    container.cipher = FernetCipher(None)
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 422
    assert "host operator" in response.text
    assert "access_token" not in response.json()


@pytest.mark.parametrize("mutation", ["expired", "inactive", "security_version", "locked"])
async def test_stale_challenges_fail_closed(
    client: AsyncClient, admin: User, clock: FakeClock, container: Container, mutation: str
) -> None:
    pending = await pending_admin(client)
    if mutation == "expired":
        clock.advance(timedelta(minutes=11))
    else:
        async with container.session_factory() as session:
            repos = container.repositories(session)
            current = await repos.users.lock_by_id(admin.id)
            assert current
            if mutation == "inactive":
                current.is_active = False
            elif mutation == "security_version":
                current.security_version += 1
            else:
                current.locked_until = clock.now() + timedelta(minutes=10)
            await repos.users.save(current)
            await repos.uow.commit()
    response = await client.post(
        "/api/auth/mfa/enrol-app", json={"challenge_token": pending["challenge_token"]}
    )
    assert response.status_code == 401


async def test_admin_email_enrolment_then_automatic_email_login(
    client: AsyncClient, admin: User, email_sender: RecordingEmailSender, container: Container
) -> None:
    email_sender.delivered = True
    pending = await pending_admin(client)
    sent = await client.post(
        "/api/auth/mfa/email", json={"challenge_token": pending["challenge_token"]}
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["email_sent"]
    code = email_sender.codes[-1][1]
    verified = await client.post(
        "/api/auth/mfa/verify",
        json={"challenge_token": pending["challenge_token"], "method": "email", "code": code},
    )
    assert verified.status_code == 200, verified.text
    async with container.session_factory() as session:
        assert await SqlMfaRepository(session).email_enabled(admin.id)
    again = await pending_admin(client)
    assert again["methods"] == ["email"] and again["email_sent"]
    assert not again["enrollment_required"]


async def test_failed_mail_cannot_be_used(
    client: AsyncClient, admin: User, email_sender: RecordingEmailSender
) -> None:
    pending = await pending_admin(client)
    sent = await client.post(
        "/api/auth/mfa/email", json={"challenge_token": pending["challenge_token"]}
    )
    assert sent.status_code == 422
    if email_sender.codes:
        result = await client.post(
            "/api/auth/mfa/verify",
            json={
                "challenge_token": pending["challenge_token"],
                "method": "email",
                "code": email_sender.codes[-1][1],
            },
        )
        assert result.status_code == 401


async def test_five_wrong_codes_exhaust_challenge(client: AsyncClient, admin: User) -> None:
    pending = await pending_admin(client)
    for _ in range(5):
        result = await client.post(
            "/api/auth/mfa/verify",
            json={
                "challenge_token": pending["challenge_token"],
                "method": "email",
                "code": "000000",
            },
        )
        assert result.status_code == 401, result.text
    assert (
        await client.post(
            "/api/auth/mfa/enrol-app", json={"challenge_token": pending["challenge_token"]}
        )
    ).status_code in (401, 429)


async def test_delivery_rechecks_security_version(
    client: AsyncClient,
    admin: User,
    container: Container,
    email_sender: RecordingEmailSender,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email_sender.delivered = True
    pending = await pending_admin(client)

    async def changed_during_mail(to_email: str, code: str) -> bool:
        async with container.session_factory() as session:
            repos = container.repositories(session)
            current = await repos.users.lock_by_id(admin.id)
            assert current
            current.security_version += 1
            await repos.users.save(current)
            await repos.uow.commit()
        return True

    monkeypatch.setattr(email_sender, "send_code", changed_during_mail)
    response = await client.post(
        "/api/auth/mfa/email", json={"challenge_token": pending["challenge_token"]}
    )
    assert response.status_code == 401


async def test_resend_invalidates_old_email_code(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
    email_sender: RecordingEmailSender,
) -> None:
    email_sender.delivered = True
    pending = await pending_admin(client)
    body = {"challenge_token": pending["challenge_token"]}
    assert (await client.post("/api/auth/mfa/email", json=body)).status_code == 200
    old = email_sender.codes[-1][1]
    clock.advance(timedelta(seconds=61))
    assert (await client.post("/api/auth/mfa/email", json=body)).status_code == 200
    new = email_sender.codes[-1][1]
    # A rare randomly equal value represents the current code too; force a different old proof.
    invalid = old if old != new else f"{(int(old) + 1) % 1_000_000:06d}"
    assert (
        await client.post("/api/auth/mfa/verify", json={**body, "method": "email", "code": invalid})
    ).status_code == 401
    assert (
        await client.post("/api/auth/mfa/verify", json={**body, "method": "email", "code": new})
    ).status_code == 200

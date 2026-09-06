"""Recovery is password-bound, single-use, scoped and invalidated by security changes."""

from datetime import timedelta

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.recovery_codes import SqlRecoveryCodeRepository
from ase.adapters.persistence.recovery_models import RecoveryCodeRow
from ase.adapters.persistence.totp import SqlTotpRepository
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
    password_login,
)
from test_mfa_personal import enrol_email


async def app_code(container: Container, admin: User, clock: FakeClock) -> str:
    clock.advance(timedelta(seconds=30))
    async with container.session_factory() as session:
        state = await SqlTotpRepository(session).get(admin.id)
        assert state and state.secret_encrypted
        return pyotp.TOTP(container.cipher.decrypt(state.secret_encrypted)).at(clock.now())


async def issue(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
    headers: dict[str, str],
) -> list[str]:
    response = await client.post(
        "/api/auth/mfa/recovery/generate",
        headers=headers,
        json={
            "password": ADMIN_PASSWORD,
            "method": "authenticator",
            "code": await app_code(container, admin, clock),
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["codes"]


async def test_codes_hash_only_and_single_use_login(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    codes = await issue(client, container, admin, clock, headers)
    assert len(set(codes)) == 10 and all(len(code) == 32 for code in codes)
    async with container.session_factory() as session:
        hashes = (await session.scalars(select(RecoveryCodeRow.code_hash))).all()
        assert len(hashes) == 10 and not set(hashes).intersection(codes)
    pending = (await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).json()
    assert "recovery" in pending["methods"]
    result = await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": pending["challenge_token"],
            "method": "recovery",
            "code": codes[0].lower(),
        },
    )
    assert result.status_code == 200, result.text
    assert (
        await client.get("/api/admin/users", headers=bearer(result.json()["access_token"]))
    ).status_code == 200
    assert (await client.get("/api/auth/mfa/recovery", headers=headers)).json()["remaining"] == 9
    pending = (await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).json()
    assert (
        await client.post(
            "/api/auth/mfa/verify",
            json={
                "challenge_token": pending["challenge_token"],
                "method": "recovery",
                "code": codes[0],
            },
        )
    ).status_code == 401


async def test_rotation_invalidates_batch_and_security_version_invalidates_remaining(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    original = await issue(client, container, admin, clock, headers)
    replacement = await issue(client, container, admin, clock, headers)
    async with container.session_factory() as session:
        user = await container.repositories(session).users.lock_by_id(admin.id)
        assert user
        repo = SqlRecoveryCodeRepository(session)
        assert not await repo.consume(
            user.id, user.security_version, container.generator.hash(original[0])
        )
        assert await repo.count(user.id, user.security_version) == 10
        user.security_version += 1
        await container.repositories(session).users.save(user)
        await session.commit()
    pending = (await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).json()
    assert "recovery" not in pending["methods"]
    assert (
        await client.post(
            "/api/auth/mfa/verify",
            json={
                "challenge_token": pending["challenge_token"],
                "method": "recovery",
                "code": replacement[0],
            },
        )
    ).status_code == 401


async def test_no_factor_cannot_generate_and_recovery_is_not_admin_enrolment(
    client: AsyncClient, user: User, admin: User
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get("/api/auth/mfa/recovery", headers=headers)).json() == {
        "remaining": 0,
        "available": False,
    }
    assert (
        await client.post(
            "/api/auth/mfa/recovery/generate",
            headers=headers,
            json={"password": USER_PASSWORD, "method": "authenticator", "code": "123456"},
        )
    ).status_code == 422
    pending = (await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).json()
    assert pending["enrollment_required"]
    assert (
        await client.post(
            "/api/auth/mfa/verify",
            json={
                "challenge_token": pending["challenge_token"],
                "method": "recovery",
                "code": "A" * 32,
            },
        )
    ).status_code == 401


async def test_email_generation_requires_own_purpose_and_fresh_password(
    client: AsyncClient, user: User, email_sender: RecordingEmailSender, clock: FakeClock
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    proof = await enrol_email(client, email_sender, headers, USER_PASSWORD)
    assert (
        await client.post("/api/auth/mfa/email/enrol/confirm", headers=headers, json=proof)
    ).status_code == 204
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    wrong = await client.post(
        "/api/auth/mfa/password-change", headers=headers, json={"password": USER_PASSWORD}
    )
    payload = {
        "password": USER_PASSWORD,
        "method": "email",
        "code": email_sender.codes[-1][1],
        "challenge_token": wrong.json()["challenge_token"],
    }
    assert (
        await client.post("/api/auth/mfa/recovery/generate", headers=headers, json=payload)
    ).status_code == 422
    clock.advance(timedelta(seconds=301))
    challenge = await client.post(
        "/api/auth/mfa/recovery/challenge", headers=headers, json={"password": USER_PASSWORD}
    )
    assert challenge.status_code == 200, challenge.text
    payload.update(
        challenge_token=challenge.json()["challenge_token"], code=email_sender.codes[-1][1]
    )
    assert (
        await client.post(
            "/api/auth/mfa/recovery/generate",
            headers=headers,
            json={**payload, "password": "wrong"},
        )
    ).status_code == 422
    assert (
        await client.post("/api/auth/mfa/recovery/generate", headers=headers, json=payload)
    ).status_code == 200
    assert (
        await client.post("/api/auth/mfa/recovery/generate", headers=headers, json=payload)
    ).status_code == 422


@pytest.mark.parametrize(
    ("method", "code"),
    [
        ("email", "A" * 32),
        ("authenticator", "A" * 32),
        ("recovery", "123456"),
        ("recovery", "Z" * 32),
    ],
)
async def test_code_schema_keeps_methods_distinct(
    client: AsyncClient, method: str, code: str
) -> None:
    assert (
        await client.post(
            "/api/auth/mfa/verify",
            json={"challenge_token": "x" * 32, "method": method, "code": code},
        )
    ).status_code == 422


async def test_recovery_cannot_bypass_password_or_last_admin_factor(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await issue(client, container, admin, clock, headers)
    assert (await password_login(client, ADMIN_EMAIL, "wrong")).status_code == 401
    response = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={
            "password": ADMIN_PASSWORD,
            "code": await app_code(container, admin, clock),
        },
    )
    assert response.status_code == 422 and "at least one MFA" in response.text


async def test_recovery_row_consumption_rolls_back_and_is_account_scoped(
    container: Container,
    user: User,
    admin: User,
) -> None:
    code_hash = container.generator.hash("A" * 32)
    async with container.session_factory() as session:
        repo = SqlRecoveryCodeRepository(session)
        await repo.replace(user.id, user.security_version, [code_hash])
        await session.commit()
        assert not await repo.consume(admin.id, admin.security_version, code_hash)
        assert await repo.consume(user.id, user.security_version, code_hash)
        await session.rollback()
        assert await repo.consume(user.id, user.security_version, code_hash)
        await session.commit()
        assert not await repo.consume(user.id, user.security_version, code_hash)


async def test_expired_challenge_does_not_consume_recovery_code(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    codes = await issue(client, container, admin, clock, headers)
    pending = (await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).json()
    clock.advance(timedelta(minutes=11))
    result = await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": pending["challenge_token"],
            "method": "recovery",
            "code": codes[0],
        },
    )
    assert result.status_code == 401
    async with container.session_factory() as session:
        current = await container.repositories(session).users.get_by_id(admin.id)
        assert current
        assert (
            await SqlRecoveryCodeRepository(session).count(admin.id, current.security_version) == 10
        )

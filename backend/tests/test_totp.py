"""Personal TOTP proofs, replay protection and mandatory administrator factors."""

from datetime import timedelta

import pyotp
from httpx import AsyncClient

from ase.adapters.persistence.totp import SqlTotpRepository
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.users import Role, User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    csrf_headers,
    login,
    login_token,
    password_login,
    restore_session,
    token_from_link,
)
from totp_helpers import enable_totp, start_enrolment, totp_login, verify_code


async def test_enrol_confirm_login_and_replay(
    client: AsyncClient,
    user: User,
    clock: FakeClock,
    container: Container,
) -> None:
    headers, secret = await start_enrolment(client)
    status = await client.get("/api/auth/totp", headers=headers)
    assert status.json() == {"enabled": False, "available": True}
    assert secret not in status.text
    async with container.session_factory() as session:
        state = await SqlTotpRepository(session).get(user.id)
        assert state and not state.enabled and state.pending_encrypted
        assert secret not in repr(state)
        assert state.pending_encrypted != secret
    assert (await password_login(client, USER_EMAIL, USER_PASSWORD)).json().get("access_token")
    code = pyotp.TOTP(secret).at(clock.now())
    confirmed = await client.post("/api/auth/totp/confirm", headers=headers, json={"code": code})
    assert confirmed.status_code == 204
    assert (await client.get("/api/me", headers=headers)).status_code == 401
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 401
    replay = await totp_login(client, USER_EMAIL, USER_PASSWORD, code)
    assert replay.status_code == 401
    assert "set-cookie" not in replay.headers
    clock.advance(timedelta(minutes=1))
    code = pyotp.TOTP(secret).at(clock.now())
    assert (await totp_login(client, USER_EMAIL, USER_PASSWORD, code)).status_code == 200
    refresh = client.cookies.get("ase_refresh") or ""
    csrf = client.cookies.get("ase_csrf") or ""
    assert (await totp_login(client, USER_EMAIL, USER_PASSWORD, code)).status_code == 401
    # A new password stage clears browser cookies but does not revoke this verified family.
    headers = restore_session(client, refresh, csrf)
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 200
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 100)
        assert any(entry.action is AuditAction.TOTP_ENABLED for entry in entries)
        assert secret not in repr(entries)


async def test_wrong_expired_and_replaced_enrolment(
    client: AsyncClient,
    user: User,
    clock: FakeClock,
) -> None:
    headers, old = await start_enrolment(client)
    replaced = await client.post(
        "/api/auth/totp/enrol",
        headers=headers,
        json={"password": USER_PASSWORD},
    )
    assert replaced.status_code == 200
    secret = replaced.json()["secret"]
    assert secret != old
    wrong = await client.post(
        "/api/auth/totp/confirm",
        headers=headers,
        json={
            "code": pyotp.TOTP(old).at(clock.now()),
        },
    )
    assert wrong.status_code == 422
    clock.advance(timedelta(minutes=11))
    expired = await client.post(
        "/api/auth/totp/confirm",
        headers=headers,
        json={
            "code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert expired.status_code == 422
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200


async def test_disable_requires_password_and_unused_code(
    client: AsyncClient,
    user: User,
    clock: FakeClock,
) -> None:
    headers, secret = await start_enrolment(client)
    confirmed = await client.post(
        "/api/auth/totp/confirm",
        headers=headers,
        json={"code": pyotp.TOTP(secret).at(clock.now())},
    )
    assert confirmed.status_code == 204
    clock.advance(timedelta(minutes=1))
    signed_in = await totp_login(
        client, USER_EMAIL, USER_PASSWORD, pyotp.TOTP(secret).at(clock.now())
    )
    headers = bearer(signed_in.json()["access_token"])
    assert (
        await client.post(
            "/api/auth/totp/enrol",
            headers=headers,
            json={
                "password": USER_PASSWORD,
            },
        )
    ).status_code == 422
    clock.advance(timedelta(minutes=1))
    code = pyotp.TOTP(secret).at(clock.now())
    wrong = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={
            "password": "incorrect-password",
            "code": code,
        },
    )
    assert wrong.status_code == 422
    wrong = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={
            "password": USER_PASSWORD,
            "code": pyotp.TOTP(secret).at(clock.now() - timedelta(minutes=5)),
        },
    )
    assert wrong.status_code == 422
    assert (await client.get("/api/auth/totp", headers=headers)).json()["enabled"] is True
    removed = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={
            "password": USER_PASSWORD,
            "code": code,
        },
    )
    assert removed.status_code == 204
    assert (await client.get("/api/auth/totp", headers=headers)).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get("/api/auth/totp", headers=headers)).json()["enabled"] is False


async def test_enrolment_limits_and_anonymous_requests_are_enforced(
    client: AsyncClient,
    user: User,
) -> None:
    assert (await client.get("/api/auth/totp")).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get("/api/auth/totp", headers=headers)).status_code == 200
    for _ in range(5):
        response = await client.post(
            "/api/auth/totp/enrol", headers=headers, json={"password": "wrong"}
        )
        assert response.status_code == 422
    response = await client.post(
        "/api/auth/totp/enrol", headers=headers, json={"password": USER_PASSWORD}
    )
    assert response.status_code == 429
    assert "retry-after" in response.headers


async def test_administrator_cannot_disable_final_factor(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
) -> None:
    headers, secret = await enable_totp(client, clock)
    clock.advance(timedelta(minutes=1))
    response = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={"password": ADMIN_PASSWORD, "code": pyotp.TOTP(secret).at(clock.now())},
    )
    assert response.status_code == 422
    assert "at least one MFA" in response.text
    assert (await client.get("/api/auth/totp", headers=headers)).json()["enabled"]


async def test_bad_totp_uses_existing_account_lockout(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
) -> None:
    _, secret = await enable_totp(client, clock)
    clock.advance(timedelta(minutes=1))
    pending = await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    challenge = pending.json()["challenge_token"]
    stale_code = pyotp.TOTP(secret).at(clock.now() - timedelta(minutes=5))
    for _ in range(5):
        assert (await verify_code(client, challenge, stale_code)).status_code == 401
    clock.advance(timedelta(minutes=1))
    assert (await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401


async def test_password_reset_preserves_totp(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
) -> None:
    headers, _ = await enable_totp(client, clock)
    reset = await client.post(f"/api/admin/users/{admin.id}/reset-link", headers=headers)
    assert reset.status_code == 200, reset.text
    new_password = "New-Observatory-Password-2026"
    response = await client.post(
        "/api/auth/set-password",
        json={
            "token": token_from_link(reset.json()["reset_link"]),
            "new_password": new_password,
        },
    )
    assert response.status_code == 204
    clock.advance(timedelta(minutes=1))
    pending = await password_login(client, ADMIN_EMAIL, new_password)
    assert pending.status_code == 200 and pending.json()["mfa_required"]
    assert "access_token" not in pending.json()


async def test_disabled_users_are_rejected_and_demoted_users_keep_personal_totp(
    client: AsyncClient,
    admin: User,
    container: Container,
    clock: FakeClock,
) -> None:
    headers, _ = await enable_totp(client, clock)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        admin = await repos.users.get_by_id(admin.id)
        assert admin
        admin.is_active = False
        await repos.users.save(admin)
        await repos.uow.commit()
    assert (await client.get("/api/auth/totp", headers=headers)).status_code == 401
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401
    async with container.session_factory() as session:
        repos = container.repositories(session)
        admin.is_active = True
        admin.role = Role.USER
        await repos.users.save(admin)
        await repos.uow.commit()
    assert (await client.get("/api/auth/totp", headers=headers)).status_code == 200
    # The enrolled factor survives demotion. Promotion cannot bypass it.
    async with container.session_factory() as session:
        repos = container.repositories(session)
        admin.role = Role.ADMIN
        await repos.users.save(admin)
        await repos.uow.commit()
    pending = await password_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert pending.status_code == 200 and pending.json()["mfa_required"]
    assert "access_token" not in pending.json()

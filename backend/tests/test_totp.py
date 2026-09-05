"""Administrator TOTP cannot be enabled, bypassed or removed without its required proofs."""

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
    token_from_link,
)
from totp_helpers import enable_totp, start_enrolment


async def test_enrol_confirm_login_and_replay(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
    container: Container,
) -> None:
    headers, secret = await start_enrolment(client)
    status = await client.get("/api/auth/totp", headers=headers)
    assert status.json() == {"enabled": False, "available": True}
    assert secret not in status.text
    async with container.session_factory() as session:
        state = await SqlTotpRepository(session).get(admin.id)
        assert state and not state.enabled and state.pending_encrypted
        assert secret not in repr(state)
        assert state.pending_encrypted != secret
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 200
    code = pyotp.TOTP(secret).at(clock.now())
    confirmed = await client.post("/api/auth/totp/confirm", headers=headers, json={"code": code})
    assert confirmed.status_code == 204
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 401
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401
    replay = await client.post(
        "/api/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "totp_code": code,
        },
    )
    assert replay.status_code == 401
    assert "set-cookie" not in replay.headers
    clock.advance(timedelta(minutes=1))
    code = pyotp.TOTP(secret).at(clock.now())
    payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "totp_code": code}
    assert (await client.post("/api/auth/login", json=payload)).status_code == 200
    assert (await client.post("/api/auth/login", json=payload)).status_code == 401
    # Refresh of a session which passed TOTP does not require another code.
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 200
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 100)
        assert any(entry.action is AuditAction.TOTP_ENABLED for entry in entries)
        assert secret not in repr(entries)


async def test_wrong_expired_and_replaced_enrolment(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
) -> None:
    headers, old = await start_enrolment(client)
    replaced = await client.post(
        "/api/auth/totp/enrol",
        headers=headers,
        json={"password": ADMIN_PASSWORD},
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
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 200


async def test_disable_requires_password_and_unused_code(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
) -> None:
    headers, secret = await enable_totp(client, clock)
    assert (
        await client.post(
            "/api/auth/totp/enrol",
            headers=headers,
            json={
                "password": ADMIN_PASSWORD,
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
            "password": ADMIN_PASSWORD,
            "code": pyotp.TOTP(secret).at(clock.now() - timedelta(minutes=5)),
        },
    )
    assert wrong.status_code == 422
    assert (await client.get("/api/auth/totp", headers=headers)).json()["enabled"] is True
    removed = await client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={
            "password": ADMIN_PASSWORD,
            "code": code,
        },
    )
    assert removed.status_code == 204
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 200
    assert (await client.get("/api/auth/totp", headers=headers)).json()["enabled"] is False


async def test_enrolment_limits_and_non_admin_are_enforced(
    client: AsyncClient,
    admin: User,
    user: User,
) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    for path, payload in (
        ("enrol", {"password": USER_PASSWORD}),
        ("confirm", {"code": "123456"}),
        ("disable", {"password": USER_PASSWORD, "code": "123456"}),
    ):
        assert (
            await client.post(f"/api/auth/totp/{path}", headers=headers, json=payload)
        ).status_code == 403
    assert (await client.get("/api/auth/totp", headers=headers)).status_code == 403
    assert (await client.get("/api/auth/totp")).status_code == 401
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    for _ in range(5):
        response = await client.post(
            "/api/auth/totp/enrol", headers=headers, json={"password": "wrong"}
        )
        assert response.status_code == 422
    response = await client.post(
        "/api/auth/totp/enrol", headers=headers, json={"password": ADMIN_PASSWORD}
    )
    assert response.status_code == 429
    assert "retry-after" in response.headers


async def test_bad_totp_uses_existing_account_lockout(
    client: AsyncClient,
    admin: User,
    clock: FakeClock,
) -> None:
    await enable_totp(client, clock)
    clock.advance(timedelta(minutes=1))
    for _ in range(5):
        assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 429
    clock.advance(timedelta(minutes=1))
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401


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
    assert (await login(client, ADMIN_EMAIL, new_password)).status_code == 401


async def test_disabled_and_demoted_users_cannot_manage_totp(
    client: AsyncClient,
    admin: User,
    container: Container,
    clock: FakeClock,
) -> None:
    headers, _ = await enable_totp(client, clock)
    async with container.session_factory() as session:
        repos = container.repositories(session)
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
    assert (await client.get("/api/auth/totp", headers=headers)).status_code == 403
    # The enrolled factor survives demotion. Promotion cannot bypass it.
    async with container.session_factory() as session:
        repos = container.repositories(session)
        admin.role = Role.ADMIN
        await repos.users.save(admin)
        await repos.uow.commit()
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401

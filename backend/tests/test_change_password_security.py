"""Credential changes retain factor requirements and serialise with reset redemption."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pyotp
import pytest
from httpx import AsyncClient

from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork
from ase.adapters.persistence.totp import SqlTotpRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, InvalidToken, Unauthenticated
from ase.domain.users import Role, User
from helpers import ADMIN_PASSWORD, USER_PASSWORD, FakeClock, bearer, create_user, login_token
from password_change_helpers import NEW_PASSWORD, outstanding_link
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414
from totp_helpers import enable_totp


async def test_password_change_and_reset_have_exactly_one_winner(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = race_container
    user = await create_user(container, email="race-password@example.com", password=USER_PASSWORD)
    reset = await outstanding_link(container, user)
    barrier = asyncio.Barrier(2)
    lock = SqlUserRepository.lock_by_id

    async def synchronise(self: SqlUserRepository, identity: UUID) -> User | None:
        await barrier.wait()
        return await lock(self, identity)

    monkeypatch.setattr(SqlUserRepository, "lock_by_id", synchronise)
    reset_password = "Competing-Reset-Password-2026"

    async def change() -> None:
        async with container.session_factory() as session:
            await container.change_password(session).execute(
                user, USER_PASSWORD, NEW_PASSWORD, CONTEXT
            )

    async def redeem() -> None:
        async with container.session_factory() as session:
            await container.set_password(session).execute(reset, reset_password, CONTEXT)

    outcomes = await asyncio.wait_for(
        asyncio.gather(change(), redeem(), return_exceptions=True), 15
    )
    assert sum(outcome is None for outcome in outcomes) == 1, outcomes
    assert sum(isinstance(outcome, (InvalidToken, Unauthenticated)) for outcome in outcomes) == 1
    expected = NEW_PASSWORD if outcomes[0] is None else reset_password
    async with container.session_factory() as session:
        current = await container.repositories(session).users.get_by_id(user.id)
        assert current and current.security_version == 1
        assert container.hasher.verify(current.password_hash or "", expected)


@pytest.mark.parametrize("state", ["inactive", "stale", "locked", "missing_password"])
async def test_application_rechecks_authoritative_account_before_password_change(
    container: Container,
    user: User,
    state: str,
) -> None:
    changes: dict[str, object] = {
        "inactive": {"is_active": False},
        "stale": {"security_version": 1},
        "locked": {"locked_until": container.clock.now() + timedelta(minutes=5)},
        "missing_password": {"password_hash": None},
    }[state]
    async with container.session_factory() as session:
        await container.repositories(session).users.save(replace(user, **changes))
        await session.commit()
    error = Unauthenticated if state in {"inactive", "stale"} else InvalidRequest
    async with container.session_factory() as session:
        with pytest.raises(error):
            await container.change_password(session).execute(
                user, USER_PASSWORD, NEW_PASSWORD, CONTEXT
            )


async def test_demoted_admin_still_needs_stored_factor_to_change_password(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    _, secret = await enable_totp(client, clock)
    async with container.session_factory() as session:
        users = container.repositories(session).users
        current = await users.get_by_id(admin.id)
        assert current
        current.role = Role.USER
        current.security_version += 1
        await users.save(current)
        await session.commit()
    clock.advance(timedelta(minutes=1))
    response = await client.post(
        "/api/auth/login",
        json={
            "email": admin.email,
            "password": ADMIN_PASSWORD,
            "totp_code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert response.status_code == 200 and response.json()["user"]["role"] == "user"
    headers = bearer(response.json()["access_token"])
    body = {"current_password": ADMIN_PASSWORD, "new_password": NEW_PASSWORD}
    assert (await client.post("/api/me/password", headers=headers, json=body)).status_code == 422
    clock.advance(timedelta(minutes=1))
    changed = await client.post(
        "/api/me/password",
        headers=headers,
        json={
            **body,
            "totp_code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert changed.status_code == 204
    async with container.session_factory() as session:
        factor = await SqlTotpRepository(session).get(admin.id)
        assert factor and factor.enabled


async def test_ip_budget_covers_attempts_across_accounts(
    client: AsyncClient, container: Container
) -> None:
    actors = [
        await create_user(container, email=f"rate-{index}@example.com", password=USER_PASSWORD)
        for index in range(3)
    ]
    tokens = [await login_token(client, actor.email, USER_PASSWORD) for actor in actors]
    body = {"current_password": "Incorrect-Current-Password", "new_password": NEW_PASSWORD}
    for index in (0, 0, 0, 1, 1):
        assert (
            await client.post("/api/me/password", headers=bearer(tokens[index]), json=body)
        ).status_code == 422
    final = await client.post("/api/me/password", headers=bearer(tokens[2]), json=body)
    assert final.status_code == 429


async def test_failed_transaction_does_not_consume_authenticator_code(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, secret = await enable_totp(client, clock)
    clock.advance(timedelta(minutes=1))
    code = pyotp.TOTP(secret).at(clock.now())
    original_hash = container.hasher.hash

    def failing_hash(_password: str) -> str:
        raise RuntimeError("Synthetic hashing failure")

    monkeypatch.setattr(container.hasher, "hash", failing_hash)
    with pytest.raises(RuntimeError, match="Synthetic hashing failure"):
        async with container.session_factory() as session:
            current = await container.repositories(session).users.get_by_id(admin.id)
            assert current
            await container.change_password(session).execute(
                current,
                ADMIN_PASSWORD,
                NEW_PASSWORD,
                CONTEXT,
                code,
            )
    monkeypatch.setattr(container.hasher, "hash", original_hash)
    response = await client.post(
        "/api/me/password",
        headers=headers,
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": NEW_PASSWORD,
            "totp_code": code,
        },
    )
    assert response.status_code == 204


async def test_failed_commit_rolls_back_credentials_sessions_links_and_audit(
    client: AsyncClient,
    container: Container,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    refresh = client.cookies.get("ase_refresh") or ""
    reset = await outstanding_link(container, user)

    async def fail_commit(_self: SqlAlchemyUnitOfWork) -> None:
        raise RuntimeError("Synthetic commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="Synthetic commit failure"):
            async with container.session_factory() as session:
                await container.change_password(session).execute(
                    user, USER_PASSWORD, NEW_PASSWORD, CONTEXT
                )

    assert (await client.get("/api/me", headers=bearer(token))).status_code == 200
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.users.get_by_id(user.id)
        refresh_record = await repos.refresh_tokens.get_by_hash(container.generator.hash(refresh))
        reset_record = await repos.password_tokens.get_by_hash(container.generator.hash(reset))
        audit = await repos.audit.list_before(None, 50)
        assert current and current.security_version == user.security_version
        assert container.hasher.verify(current.password_hash or "", USER_PASSWORD)
        assert refresh_record and refresh_record.revoked_at is None
        assert reset_record and reset_record.used_at is None
        assert all(entry.action is not AuditAction.PASSWORD_CHANGED for entry in audit)

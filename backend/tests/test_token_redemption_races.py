"""Single-use token claims survive concurrent stale reads in independent DB sessions."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import RefreshTokenRow
from ase.adapters.persistence.tokens import SqlPasswordTokenRepository, SqlRefreshTokenRepository
from ase.application.dto import AuthSession
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRefreshToken, InvalidToken
from ase.domain.tokens import PasswordToken, RefreshToken, TokenPurpose
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414


def synchronise_refresh_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    original = SqlRefreshTokenRepository.get_by_hash
    barrier = asyncio.Barrier(2)
    calls = 0

    async def stale_read(self: SqlRefreshTokenRepository, token_hash: str) -> RefreshToken | None:
        nonlocal calls
        token = await original(self, token_hash)
        calls += 1
        if calls <= 2:
            await barrier.wait()
        return token

    monkeypatch.setattr(SqlRefreshTokenRepository, "get_by_hash", stale_read)


def synchronise_password_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    original = SqlPasswordTokenRepository.get_by_hash
    barrier = asyncio.Barrier(2)

    async def stale_read(self: SqlPasswordTokenRepository, token_hash: str) -> PasswordToken | None:
        token = await original(self, token_hash)
        await barrier.wait()
        return token

    monkeypatch.setattr(SqlPasswordTokenRepository, "get_by_hash", stale_read)


async def test_refresh_race_issues_one_child_then_revokes_family(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
    synchronise_refresh_reads(monkeypatch)

    async def redeem() -> AuthSession:
        async with container.session_factory() as session:
            return await container.refresh(session).execute(initial.refresh_secret, CONTEXT)

    results = await asyncio.gather(redeem(), redeem(), return_exceptions=True)
    successes = [result for result in results if isinstance(result, AuthSession)]
    assert len(successes) == 1
    assert sum(isinstance(result, InvalidRefreshToken) for result in results) == 1
    async with container.session_factory() as session:
        rows = list(await session.scalars(select(RefreshTokenRow)))
        assert len(rows) == 2  # One parent and exactly one child.
        assert all(row.revoked_at is not None for row in rows)
        entries = await container.repositories(session).audit.list_before(None, 100)
        assert any(entry.action is AuditAction.REFRESH_REUSE_DETECTED for entry in entries)
        assert all(
            str(row.family_id) not in str(entry.details) for row in rows for entry in entries
        )
        assert all(row.user_id == user.id for row in rows)
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(successes[0].refresh_secret, CONTEXT)


async def test_password_race_changes_password_exactly_once(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    secret = container.generator.new_secret()
    now = container.clock.now()
    token = PasswordToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=container.generator.hash(secret),
        purpose=TokenPurpose.RESET,
        expires_at=now + timedelta(minutes=30),
        used_at=None,
        created_at=now,
    )
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.password_tokens.add(token)
        await repos.uow.commit()
    synchronise_password_reads(monkeypatch)
    passwords = ("First-Observatory-Password-2026", "Second-Observatory-Password-2026")

    async def redeem(password: str) -> None:
        async with container.session_factory() as session:
            await container.set_password(session).execute(secret, password, CONTEXT)

    results = await asyncio.gather(
        *(redeem(password) for password in passwords), return_exceptions=True
    )
    winners = [index for index, result in enumerate(results) if result is None]
    assert len(winners) == 1, results
    assert sum(isinstance(result, InvalidToken) for result in results) == 1
    async with container.session_factory() as session:
        repos = container.repositories(session)
        stored = await repos.users.get_by_id(user.id)
        assert stored is not None and stored.password_hash is not None
        assert container.hasher.verify(stored.password_hash, passwords[winners[0]])
        assert not container.hasher.verify(stored.password_hash, passwords[1 - winners[0]])
        entries = await repos.audit.list_before(None, 100)
        assert sum(entry.action is AuditAction.PASSWORD_SET for entry in entries) == 1


@pytest.mark.parametrize("kind", ["refresh", "password"])
async def test_token_claim_is_rolled_back_and_rejects_expiry(
    race_container: Container,
    kind: str,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    now = container.clock.now()
    token_id = uuid4()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        if kind == "refresh":
            await repos.refresh_tokens.add(
                RefreshToken(
                    id=token_id,
                    user_id=user.id,
                    token_hash=container.generator.hash("fixture-refresh"),
                    family_id=uuid4(),
                    parent_id=None,
                    issued_at=now,
                    expires_at=now + timedelta(minutes=1),
                    revoked_at=None,
                    ip=None,
                    user_agent=None,
                )
            )
        else:
            await repos.password_tokens.add(
                PasswordToken(
                    id=token_id,
                    user_id=user.id,
                    token_hash=container.generator.hash("fixture-password"),
                    purpose=TokenPurpose.RESET,
                    expires_at=now + timedelta(minutes=1),
                    used_at=None,
                    created_at=now,
                )
            )
        await repos.uow.commit()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        repo = repos.refresh_tokens if kind == "refresh" else repos.password_tokens
        assert await repo.consume(token_id, now)
        # A downstream failure must leave the token available for a valid retry.
        await repos.uow.rollback()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        repo = repos.refresh_tokens if kind == "refresh" else repos.password_tokens
        assert not await repo.consume(uuid4(), now)
        assert not await repo.consume(token_id, now + timedelta(minutes=1))
        assert await repo.consume(token_id, now)
        assert not await repo.consume(token_id, now)
        await repos.uow.commit()

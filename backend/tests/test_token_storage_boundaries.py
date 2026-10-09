"""Persisted token edits preserve identity, expiry and revocation guarantees."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence.session import engine_options
from ase.adapters.persistence.token_families import record_family_revocation
from ase.adapters.persistence.tokens import SqlPasswordTokenRepository, SqlRefreshTokenRepository
from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.errors import InvalidToken, NotFound
from ase.domain.session_activity import SessionIdlePolicy
from ase.domain.tokens import PasswordToken, RefreshToken, TokenPurpose
from ase.domain.users import User
from helpers import FakeClock
from mfa_boundary_support import NOW


async def test_refresh_save_persists_revocation_and_expiry_but_not_identity(
    container: Container, user: User, clock: FakeClock
) -> None:
    token = RefreshToken(
        uuid4(),
        user.id,
        "refresh-hash",
        uuid4(),
        None,
        clock.now(),
        clock.now() + timedelta(days=1),
        None,
        None,
        None,
    )
    async with container.session_factory() as session:
        repo = SqlRefreshTokenRepository(session, SessionIdlePolicy())
        await repo.add(token)
        token.revoked_at = clock.now()
        token.expires_at = clock.now() + timedelta(hours=1)
        await repo.save(replace(token, token_hash="must-not-replace-hash"))
        with pytest.raises(NotFound):
            await repo.save(replace(token, id=uuid4()))
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlRefreshTokenRepository(session, SessionIdlePolicy())
        saved = await repo.get_by_hash("refresh-hash")
        assert saved == token
        assert await repo.get_by_hash("must-not-replace-hash") is None
        assert not await repo.family_is_active(user.id, token.family_id, clock.now())


async def test_password_save_persists_use_without_replacing_identity(
    container: Container, user: User, clock: FakeClock
) -> None:
    token = PasswordToken(
        uuid4(),
        user.id,
        "password-hash",
        TokenPurpose.RESET,
        clock.now() + timedelta(hours=1),
        None,
        clock.now(),
    )
    async with container.session_factory() as session:
        repo = SqlPasswordTokenRepository(session)
        await repo.add(token)
        token.used_at = clock.now()
        await repo.save(replace(token, token_hash="must-not-replace-hash"))
        with pytest.raises(NotFound):
            await repo.save(replace(token, id=uuid4()))
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlPasswordTokenRepository(session)
        assert await repo.get_by_hash("password-hash") == token
        assert await repo.get_by_hash("must-not-replace-hash") is None
        assert not await repo.consume(token.id, clock.now())


async def test_revoking_empty_family_blocks_late_arriving_descendant(
    container: Container, user: User, clock: FakeClock
) -> None:
    family = uuid4()
    async with container.session_factory() as session:
        repo = SqlRefreshTokenRepository(session, SessionIdlePolicy())
        assert await repo.revoke_family(family, clock.now()) == 0
        await session.commit()
    token = RefreshToken(
        uuid4(),
        user.id,
        "late-descendant",
        family,
        None,
        clock.now(),
        clock.now() + timedelta(days=1),
        None,
        None,
        None,
    )
    async with container.session_factory() as session:
        repo = SqlRefreshTokenRepository(session, SessionIdlePolicy())
        await repo.add(token)
        await session.commit()
        assert not await repo.family_is_active(user.id, family, clock.now())
        assert not await repo.consume(token.id, clock.now())


async def test_postgres_family_revocation_statement_is_bound_and_conflict_safe() -> None:
    # Compile against the real dialect without contacting an external database.
    engine = create_async_engine("postgresql+asyncpg://localhost/unused")
    session = AsyncMock()
    session.get_bind = lambda: engine.sync_engine
    family = uuid4()
    try:
        await record_family_revocation(session, family, NOW)
        statement = session.execute.call_args.args[0]
        compiled = statement.compile(dialect=dialect())
        assert "ON CONFLICT (family_id) DO NOTHING" in str(compiled)
        assert str(family) not in str(compiled)
        assert compiled.params["family_id"] == family
        assert compiled.params["revoked_at"] == NOW
    finally:
        await engine.dispose()


def test_other_dialect_does_not_inherit_sqlite_or_postgres_pool_options() -> None:
    assert engine_options("mysql+asyncmy://localhost/unused") == {}


async def test_password_redemption_loser_cannot_change_credentials(
    container: Container, user: User, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = PasswordToken(
        uuid4(),
        user.id,
        container.generator.hash("reset-proof"),
        TokenPurpose.RESET,
        clock.now() + timedelta(hours=1),
        None,
        clock.now(),
    )
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.password_tokens.add(token)
        await session.commit()
        use_case = container.set_password(session)
        # Another worker wins the atomic claim after this worker reads the token.
        consume = AsyncMock(return_value=False)
        monkeypatch.setattr(use_case._password_tokens, "consume", consume)
        with pytest.raises(InvalidToken):
            await use_case.execute("reset-proof", "A-new-Strong-Passphrase-2026", RequestContext())
        consume.assert_awaited_once_with(token.id, clock.now())
        await session.rollback()
    async with container.session_factory() as session:
        saved = await container.repositories(session).users.get_by_id(user.id)
        assert saved and saved.password_hash == user.password_hash
        assert saved.security_version == user.security_version


async def test_reset_link_cannot_reactivate_an_account_disabled_after_issuance(
    container: Container, user: User, clock: FakeClock
) -> None:
    token = PasswordToken(
        uuid4(),
        user.id,
        container.generator.hash("disabled-proof"),
        TokenPurpose.RESET,
        clock.now() + timedelta(hours=1),
        None,
        clock.now(),
    )
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.password_tokens.add(token)
        disabled = replace(user, is_active=False)
        await repos.users.save(disabled)
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(InvalidToken):
            await container.set_password(session).execute(
                "disabled-proof", "A-new-Strong-Passphrase-2026", RequestContext()
            )
        await session.rollback()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        saved = await repos.users.get_by_id(user.id)
        assert saved and not saved.is_active and saved.password_hash == user.password_hash
        stored = await repos.password_tokens.get_by_hash(token.token_hash)
        assert stored and stored.used_at is None

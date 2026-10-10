"""Awaited authority reads must not outlive the access or idle deadline."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from ase.adapters.persistence.firms_credentials import FirmsCredentialRow
from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.tokens import SqlRefreshTokenRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.auth.current_session import validate_current_session
from ase.domain.audit import AuditAction
from ase.domain.errors import SessionIdleExpired, Unauthenticated
from helpers import USER_EMAIL, USER_PASSWORD
from team_helpers import CONTEXT
from test_firms_credentials import call, ready
from test_firms_credentials import probe as probe  # noqa: PLC0414
from test_saved_map_views import claims_for


@pytest.mark.parametrize("expiry", ["access", "idle"])
async def test_expiry_during_precommit_family_read_rolls_back_confirmation(
    client, container, admin, probe, clock, monkeypatch, expiry
):
    if expiry == "idle":
        container.settings.admin_session_idle_minutes = 5
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    read = SqlRefreshTokenRepository.family_is_active
    reads = 0

    async def cross_deadline(repository, *args, **kwargs):
        nonlocal reads
        result = await read(repository, *args, **kwargs)
        reads += 1
        if reads == 2:  # Admission succeeds; cross the deadline in pre-commit validation.
            assert result is True
            clock.advance(timedelta(minutes=5 if expiry == "idle" else 16))
        return result

    monkeypatch.setattr(SqlRefreshTokenRepository, "family_is_active", cross_deadline)
    with pytest.raises(Unauthenticated):
        await call(container, actor, "confirm", state.revision, state.test_generation, CONTEXT)
    async with container.session_factory() as session:
        row = await session.get(FirmsCredentialRow, 1)
        assert row.active_encrypted is None and row.revision == state.revision
        assert row.draft_encrypted is not None and row.tested_at == state.tested_at
        assert (
            await session.scalar(
                select(AuditLogRow.id).where(
                    AuditLogRow.action == AuditAction.FIRMS_CONFIRMED.value
                )
            )
            is None
        )


@pytest.mark.parametrize("expiry", ["access", "idle"])
@pytest.mark.parametrize("boundary", ["user", "family", "activity"])
async def test_shared_validation_rejects_deadline_crossed_during_any_read(
    container, user, clock, monkeypatch, expiry, boundary
):
    if expiry == "idle":
        container.settings.session_idle_minutes = 5
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
    claims = container.issuer.verify(initial.access.token)
    repository, method = {
        "user": (SqlUserRepository, "get_by_id"),
        "family": (SqlRefreshTokenRepository, "family_is_active"),
        "activity": (SqlRefreshTokenRepository, "activity"),
    }[boundary]
    read = getattr(repository, method)

    async def cross_deadline(instance, *args, **kwargs):
        result = await read(instance, *args, **kwargs)
        clock.advance(timedelta(minutes=5 if expiry == "idle" else 16))
        return result

    monkeypatch.setattr(repository, method, cross_deadline)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        error = SessionIdleExpired if expiry == "idle" else Unauthenticated
        with pytest.raises(error):
            await validate_current_session(claims, repos.users, repos.refresh_tokens, clock)


async def test_live_validation_preserves_activity_and_transaction(
    container, user, clock, monkeypatch
):
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
    claims = container.issuer.verify(initial.access.token)
    clock.advance(timedelta(minutes=1))
    async with container.session_factory() as session:
        repos = container.repositories(session)
        before = await repos.refresh_tokens.activity(user.id, claims.family_id, clock.now())
        commit, rollback = AsyncMock(), AsyncMock()
        monkeypatch.setattr(session, "commit", commit)
        monkeypatch.setattr(session, "rollback", rollback)
        current = await validate_current_session(claims, repos.users, repos.refresh_tokens, clock)
        assert current.id == user.id
        assert await repos.refresh_tokens.activity(user.id, claims.family_id, clock.now()) == before
        commit.assert_not_awaited()
        rollback.assert_not_awaited()

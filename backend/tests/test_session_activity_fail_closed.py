"""Missing activity cannot mint credentials, revive a family or prevent explicit logout."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import delete, select

from ase.adapters.persistence.models import AuditLogRow, RefreshTokenRow
from ase.adapters.persistence.session_activity import RefreshFamilyActivityRow
from ase.adapters.persistence.token_families import RefreshFamilyRevocationRow
from ase.adapters.persistence.tokens import SqlRefreshTokenRepository
from ase.application.auth.sessions import SessionFactory
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRefreshToken, SessionIdleExpired, Unauthenticated
from helpers import USER_EMAIL, USER_PASSWORD
from token_race_helpers import CONTEXT


@pytest.fixture
async def signed_in(container, user):
    container.settings.session_idle_minutes = 5
    async with container.session_factory() as session:
        return await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)


async def remove_activity(container, family_id):
    async with container.session_factory() as session:
        await session.execute(
            delete(RefreshFamilyActivityRow).where(RefreshFamilyActivityRow.family_id == family_id)
        )
        await session.commit()


@pytest.mark.parametrize("expired", [False, True])
async def test_heartbeat_rejects_activity_disappearing_after_validation(
    container, signed_in, clock, monkeypatch, expired
):
    claims = container.issuer.verify(signed_in.access.token)
    clock.advance(timedelta(minutes=5 if expired else 1))
    read = SqlRefreshTokenRepository.activity
    reads = 0

    async def disappearing_activity(repository, user_id, family_id, now):
        nonlocal reads
        reads += 1
        # The expiry diagnosis may see a row which the subsequent recovery read cannot.
        if expired and reads == 1:
            return await read(repository, user_id, family_id, now)
        return None

    touch = AsyncMock()
    monkeypatch.setattr(SqlRefreshTokenRepository, "activity", disappearing_activity)
    monkeypatch.setattr(SqlRefreshTokenRepository, "touch_activity", touch)
    async with container.session_factory() as session:
        commit = AsyncMock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit)
        audits = list(await session.scalars(select(AuditLogRow.id)))
        error = SessionIdleExpired if expired else Unauthenticated
        with pytest.raises(error) as rejected:
            await container.session_activity(session).execute(claims, CONTEXT)
        if expired:
            assert rejected.value.fields == {"idle_minutes": "5"}
        assert reads == (2 if expired else 1)
        touch.assert_not_awaited()
        commit.assert_not_awaited()
        assert list(await session.scalars(select(AuditLogRow.id))) == audits
        tokens = list(await session.scalars(select(RefreshTokenRow)))
        assert len(tokens) == 1 and tokens[0].revoked_at is None
        assert await session.scalar(select(RefreshFamilyRevocationRow)) is None


async def test_refresh_without_activity_cannot_consume_or_issue_credentials(
    container, signed_in, monkeypatch
):
    claims = container.issuer.verify(signed_in.access.token)
    await remove_activity(container, claims.family_id)
    issue = Mock(wraps=container.issuer.issue)
    monkeypatch.setattr(container.issuer, "issue", issue)
    async with container.session_factory() as session:
        commit = AsyncMock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit)
        audits = list(await session.scalars(select(AuditLogRow.id)))
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(signed_in.refresh_secret, CONTEXT)
        issue.assert_not_called()
        commit.assert_not_awaited()
        tokens = list(await session.scalars(select(RefreshTokenRow)))
        assert len(tokens) == 1 and tokens[0].revoked_at is None
        assert tokens[0].token_hash == container.generator.hash(signed_in.refresh_secret)
        assert await session.scalar(select(RefreshFamilyActivityRow)) is None
        assert list(await session.scalars(select(AuditLogRow.id))) == audits


@pytest.mark.parametrize("idle_only", [False, True])
async def test_logout_revokes_known_family_even_without_activity(
    container, signed_in, clock, idle_only
):
    claims = container.issuer.verify(signed_in.access.token)
    await remove_activity(container, claims.family_id)
    async with container.session_factory() as session:
        result = await container.logout(session).execute(
            signed_in.refresh_secret,
            CONTEXT,
            expected_family=claims.family_id,
            idle_only=idle_only,
        )
        assert result is True
    # A fresh transaction must observe durable revocation and its explicit logout audit.
    async with container.session_factory() as session:
        tokens = list(await session.scalars(select(RefreshTokenRow)))
        assert len(tokens) == 1 and tokens[0].revoked_at == clock.now()
        marker = await session.get(RefreshFamilyRevocationRow, claims.family_id)
        assert marker is not None
        audits = list(await session.scalars(select(AuditLogRow.action)))
        assert audits.count(AuditAction.LOGOUT.value) == 1
        assert AuditAction.SESSION_IDLE_EXPIRED.value not in audits
        assert await session.scalar(select(RefreshFamilyActivityRow)) is None


@pytest.mark.parametrize("reason", ["missing", "expired"])
async def test_session_factory_cannot_create_child_without_live_family_activity(
    container, user, signed_in, clock, monkeypatch, reason
):
    claims = container.issuer.verify(signed_in.access.token)
    if reason == "missing":
        await remove_activity(container, claims.family_id)
    else:
        clock.advance(timedelta(minutes=5))
    issue = Mock(wraps=container.issuer.issue)
    monkeypatch.setattr(container.issuer, "issue", issue)
    async with container.session_factory() as session:
        repo = container.repositories(session).refresh_tokens
        root = await repo.get_by_hash(container.generator.hash(signed_in.refresh_secret))
        assert root is not None
        factory = SessionFactory(
            repo, container.issuer, container.generator, clock, container.refresh_ttl
        )
        with pytest.raises(Unauthenticated):
            await factory.start(user, CONTEXT, family_id=claims.family_id, parent_id=root.id)
        issue.assert_not_called()
        tokens = list(await session.scalars(select(RefreshTokenRow)))
        assert [token.id for token in tokens] == [root.id]
        assert tokens[0].revoked_at is None
        activity = await repo.activity(user.id, claims.family_id, clock.now())
        if reason == "missing":
            assert activity is None
        else:
            assert activity is not None and activity.expired

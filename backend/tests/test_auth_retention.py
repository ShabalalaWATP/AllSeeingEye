"""Terminal auth erasure is bounded, opt-in and independent of account activity."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.mfa_models import EmailMfaRow, MfaChallengeRow
from ase.adapters.persistence.models import (
    AccountRequestRow,
    PasswordTokenRow,
    RefreshTokenRow,
    UserRow,
)
from ase.adapters.persistence.session_activity import RefreshFamilyActivityRow
from ase.adapters.persistence.token_families import RefreshFamilyRevocationRow
from ase.adapters.persistence.totp import AdminTotpRow
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.container.auth_retention import maintain_authentication
from ase.domain.auth_retention import FAMILY_RETENTION, LINK_RETENTION, AuthRetentionPolicy
from ase.domain.errors import InvalidRefreshToken
from auth_retention_helpers import challenge, count, password, push_family, refresh, request, seed
from helpers import USER_EMAIL, USER_PASSWORD
from token_race_helpers import CONTEXT


async def run(container, *, dry_run=False, paused=False, batch=100):
    return await maintain_authentication(
        container.session_factory,
        container.clock.now(),
        AuthRetentionPolicy(batch_size=batch, paused=paused),
        dry_run=dry_run,
    )


@pytest.mark.parametrize("offset", [-1, 0, 1])
@pytest.mark.parametrize("used", [False, True])
async def test_link_boundary(container, user, offset, used):
    now = container.clock.now()
    deadline = now - LINK_RETENTION + timedelta(microseconds=offset)
    row = password(
        user, now + timedelta(days=1) if used else deadline, used=deadline if used else None
    )
    await seed(container, row)
    counts = await run(container)
    assert counts["password_links"] == (offset <= 0)
    assert await count(container, PasswordTokenRow) == (offset > 0)


@pytest.mark.parametrize("offset", [-1, 0, 1])
@pytest.mark.parametrize("consumed", [False, True])
async def test_challenge_boundary_and_sensitive_erasure(container, user, offset, consumed):
    now = container.clock.now()
    deadline = now + timedelta(microseconds=offset)
    await seed(
        container,
        challenge(
            user,
            now + timedelta(minutes=10) if consumed else deadline,
            consumed=deadline if consumed else None,
        ),
    )
    assert (await run(container))["mfa_challenges"] == (offset <= 0)
    assert await count(container, MfaChallengeRow) == (offset > 0)


@pytest.mark.parametrize("offset", [-1, 0, 1])
@pytest.mark.parametrize("enabled", [False, True])
async def test_pending_totp_never_erases_confirmed_factor(container, user, offset, enabled):
    await seed(
        container,
        AdminTotpRow(
            user_id=user.id,
            secret_encrypted="active-factor" if enabled else None,
            pending_encrypted="abandoned-factor",
            last_step=123 if enabled else None,
            pending_expires_at=container.clock.now() + timedelta(microseconds=offset),
        ),
        EmailMfaRow(user_id=user.id, enabled=True),
    )
    assert (await run(container))["pending_totp"] == (offset <= 0)
    async with container.session_factory() as session:
        row = await session.get(AdminTotpRow, user.id)
        assert row.secret_encrypted == ("active-factor" if enabled else None)
        assert row.last_step == (123 if enabled else None)
        assert row.pending_encrypted == ("abandoned-factor" if offset > 0 else None)
        assert (await session.get(EmailMfaRow, user.id)).enabled


@pytest.mark.parametrize("offset", [-1, 0, 1])
@pytest.mark.parametrize("status", ["approved", "rejected", "pending", "unknown"])
async def test_request_boundary_and_dormant_accounts(container, user, offset, status):
    await seed(
        container,
        request(
            container.clock.now() - timedelta(days=90) + timedelta(microseconds=offset),
            status=status,
        ),
    )
    async with container.session_factory() as session:
        (await session.get(UserRow, user.id)).is_active = False
        await session.commit()
    expected = status in {"approved", "rejected"} and offset <= 0
    assert (await run(container))["account_requests"] == expected
    assert await count(container, AccountRequestRow) == (not expected)


@pytest.mark.parametrize("offset", [-1, 0, 1])
async def test_never_revoked_family_waits_for_latest_expiry(container, user, offset):
    cutoff = container.clock.now() - FAMILY_RETENTION
    old = refresh(user, cutoff - timedelta(days=30))
    latest = refresh(user, cutoff + timedelta(microseconds=offset), family=old.family_id)
    await seed(container, old, latest)
    assert (await run(container))["refresh_tokens"] == (2 if offset <= 0 else 0)
    assert await count(container, RefreshTokenRow) == (0 if offset <= 0 else 2)


async def test_live_descendant_preserves_old_replay_detection(container, user):
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
        child = await container.refresh(session).execute(initial.refresh_secret, CONTEXT)
        old = await session.scalar(
            select(RefreshTokenRow).where(
                RefreshTokenRow.token_hash == container.generator.hash(initial.refresh_secret)
            )
        )
        old.expires_at = container.clock.now() - FAMILY_RETENTION
        await session.commit()
    assert (await run(container))["refresh_tokens"] == 0
    async with container.session_factory() as session:
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(initial.refresh_secret, CONTEXT)
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(child.refresh_secret, CONTEXT)


async def test_preview_hold_and_repeat_batches(container, user):
    deadline = container.clock.now() - LINK_RETENTION
    await seed(container, *(password(user, deadline) for _ in range(5)))
    assert (await run(container, dry_run=True, batch=2))["password_links"] == 2
    assert await count(container, PasswordTokenRow) == 5
    assert await run(container, paused=True) == {}
    assert await count(container, PasswordTokenRow) == 5
    assert [(await run(container, batch=2))["password_links"] for _ in range(4)] == [2, 2, 1, 0]


async def test_push_backlog_is_drained_before_family_anchor(container, user):
    await push_family(container, user, container.clock.now() - FAMILY_RETENTION, 5)
    for remaining in (3, 1):
        result = await run(container, batch=2)
        assert result["push_receipts"] == 2
        assert result["push_devices"] == result["refresh_tokens"] == 0
        assert await count(container, PushDeliveryRow) == remaining
        assert await count(container, RefreshTokenRow) == 1
    result = await run(container, batch=2)
    assert result["push_receipts"] == result["push_devices"] == result["refresh_tokens"] == 1
    for model in (
        PushDeviceRow,
        RefreshTokenRow,
        RefreshFamilyActivityRow,
        RefreshFamilyRevocationRow,
    ):
        assert await count(container, model) == 0
    assert not any((await run(container)).values())


async def test_failed_commit_rolls_back_and_retry_succeeds(container, user, monkeypatch):
    await seed(container, password(user, container.clock.now() - LINK_RETENTION))
    original = AsyncSession.commit

    async def fail(_session):
        raise RuntimeError("injected commit failure")

    monkeypatch.setattr(AsyncSession, "commit", fail)
    with pytest.raises(RuntimeError, match="injected"):
        await run(container)
    assert await count(container, PasswordTokenRow) == 1
    monkeypatch.setattr(AsyncSession, "commit", original)
    assert (await run(container))["password_links"] == 1


async def test_unknown_deadlines_and_recent_orphan_metadata_are_retained(container, user):
    now = container.clock.now()
    undecided_date = request(now - timedelta(days=100))
    undecided_date.decided_at = None
    recent, old = uuid4(), uuid4()
    await seed(
        container,
        undecided_date,
        AdminTotpRow(user_id=user.id, pending_encrypted="unknown-deadline"),
        RefreshFamilyActivityRow(family_id=recent, user_id=user.id, last_activity_at=now),
        RefreshFamilyRevocationRow(family_id=recent, revoked_at=now),
        RefreshFamilyActivityRow(
            family_id=old, user_id=user.id, last_activity_at=now - FAMILY_RETENTION
        ),
        RefreshFamilyRevocationRow(family_id=old, revoked_at=now - FAMILY_RETENTION),
    )
    counts = await run(container)
    assert counts["account_requests"] == counts["pending_totp"] == 0
    assert counts["family_activity"] == counts["family_revocations"] == 1
    async with container.session_factory() as session:
        assert await session.get(RefreshFamilyActivityRow, recent) is not None
        assert await session.get(RefreshFamilyRevocationRow, recent) is not None


async def test_large_mixed_family_backlog_never_crosses_batch_or_owner_boundary(
    container, user, admin
):
    cutoff = container.clock.now() - FAMILY_RETENTION
    terminal, _ = await push_family(container, user, cutoff, 205)
    active, _ = await push_family(container, admin, container.clock.now() + timedelta(days=1), 3)
    recent, _ = await push_family(container, user, cutoff + timedelta(microseconds=1), 3)
    await seed(
        container,
        *(refresh(user, cutoff, family=terminal.family_id) for _ in range(249)),
        refresh(admin, cutoff - timedelta(days=10), family=active.family_id),
        refresh(user, cutoff - timedelta(days=10), family=recent.family_id),
    )
    receipts, tokens = [], []
    for _ in range(6):
        result = await run(container)
        assert all(0 <= value <= 100 for value in result.values())
        receipts.append(result["push_receipts"])
        tokens.append(result["refresh_tokens"])
    assert receipts == [100, 100, 5, 0, 0, 0]
    assert tokens == [0, 0, 100, 100, 50, 0]
    assert await count(container, PushDeliveryRow) == 6
    assert await count(container, PushDeviceRow) == 2
    assert await count(container, RefreshTokenRow) == 4

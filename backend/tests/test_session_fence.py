"""SessionFence: confirm re-reads or safely reuses a session check; release guards expiry."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.security.session_signals import InMemorySessionSignals
from ase.api.session_fence import SessionFence
from ase.application.auth.session_freshness import SessionFreshness
from ase.application.dto import AccessClaims
from ase.domain.errors import Forbidden, Unauthenticated
from ase.domain.users import Role
from helpers import FakeClock

START = datetime(2026, 9, 25, 12, tzinfo=UTC)


def claims(expires_in: timedelta = timedelta(minutes=15)) -> AccessClaims:
    return AccessClaims(
        user_id=uuid4(),
        role=Role.USER,
        jti="jti",
        expires_at=START + expires_in,
        family_id=uuid4(),
        security_version=1,
    )


def fence_with(
    check: AsyncMock, clock: FakeClock, *, token: AccessClaims | None = None
) -> tuple[SessionFence, AsyncMock, InMemorySessionSignals]:
    context = AsyncMock()
    fresh = object()
    context.__aenter__.return_value = fresh
    signals = InMemorySessionSignals(clock)
    container = SimpleNamespace(
        session_factory=lambda: context,
        clock=clock,
        repositories=lambda session: SimpleNamespace(
            users=("users", session), refresh_tokens=("tokens", session)
        ),
        session_signals=signals,
        session_freshness=SessionFreshness(clock, signals, timedelta(seconds=15)),
    )
    return SessionFence(container, token or claims()), context, signals


@pytest.fixture
def check(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=SimpleNamespace(is_admin=False))
    monkeypatch.setattr("ase.api.session_fence.validate_current_session", mock)
    return mock


async def test_confirm_opens_a_fresh_transaction_when_none_is_supplied(check: AsyncMock) -> None:
    fence, context, _ = fence_with(check, FakeClock(START))
    await fence.confirm()
    assert context.__aexit__.await_count == 1
    assert check.await_args.args[1] == ("users", context.__aenter__.return_value)


async def test_confirm_reuses_a_supplied_transaction(check: AsyncMock) -> None:
    fence, context, _ = fence_with(check, FakeClock(START))
    supplied = object()
    await fence.confirm(session=supplied)
    assert context.__aenter__.await_count == 0
    assert check.await_args.args[1] == ("users", supplied)


async def test_admin_only_rejects_a_valid_non_administrator(check: AsyncMock) -> None:
    fence, _, _ = fence_with(check, FakeClock(START))
    with pytest.raises(Forbidden):
        await fence.confirm(admin_only=True)


async def test_a_revoked_session_propagates(check: AsyncMock) -> None:
    check.side_effect = Unauthenticated("ended")
    fence, _, _ = fence_with(check, FakeClock(START))
    with pytest.raises(Unauthenticated):
        await fence.release("private")


async def test_release_returns_the_value_only_while_the_token_lives(check: AsyncMock) -> None:
    clock = FakeClock(START)
    fence, _, _ = fence_with(check, clock, token=claims(timedelta(seconds=1)))
    assert await fence.release("private") == "private"
    clock.advance(timedelta(seconds=1))
    with pytest.raises(Unauthenticated):
        fence.assert_live()
    with pytest.raises(Unauthenticated):
        await fence.release("private")


async def test_a_recent_check_is_reused_within_the_window(check: AsyncMock) -> None:
    clock = FakeClock(START)
    fence, _, _ = fence_with(check, clock)
    await fence.confirm()
    clock.advance(timedelta(seconds=14))
    await fence.confirm()
    assert check.await_count == 1
    clock.advance(timedelta(seconds=1))
    await fence.confirm()
    assert check.await_count == 2


async def test_a_signalled_change_forces_a_fresh_read(check: AsyncMock) -> None:
    clock = FakeClock(START)
    token = claims()
    fence, _, signals = fence_with(check, clock, token=token)
    await fence.confirm()
    signals.publish(token.user_id)
    check.side_effect = Unauthenticated("revoked")
    with pytest.raises(Unauthenticated):
        await fence.confirm()
    assert check.await_count == 2


async def test_admin_only_still_applies_to_a_reused_check(check: AsyncMock) -> None:
    fence, _, _ = fence_with(check, FakeClock(START))
    await fence.confirm()
    with pytest.raises(Forbidden):
        await fence.confirm(admin_only=True)
    assert check.await_count == 1

"""Freshness reuses a session check only inside its window and before any signalled change."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ase.adapters.security.session_signals import InMemorySessionSignals
from ase.application.auth.session_freshness import SessionFreshness
from ase.application.dto import AccessClaims
from ase.domain.users import Role
from helpers import FakeClock

START = datetime(2026, 9, 25, 12, tzinfo=UTC)
WINDOW = timedelta(seconds=15)


def claims(**changes: object) -> AccessClaims:
    values = {
        "user_id": uuid4(),
        "role": Role.USER,
        "jti": "jti",
        "expires_at": START + timedelta(minutes=15),
        "family_id": uuid4(),
        "security_version": 1,
    } | changes
    return AccessClaims(**values)  # type: ignore[arg-type]


def freshness(
    clock: FakeClock, capacity: int = 4
) -> tuple[SessionFreshness, InMemorySessionSignals]:
    signals = InMemorySessionSignals(clock)
    return SessionFreshness(clock, signals, WINDOW, capacity=capacity), signals


def test_a_remembered_check_is_reused_until_the_window_closes() -> None:
    clock = FakeClock(START)
    cache, _ = freshness(clock)
    token, user = claims(), SimpleNamespace(name="user")
    assert cache.recent(token) is None
    cache.remember(token, user, clock.now())
    clock.advance(WINDOW - timedelta(microseconds=1))
    assert cache.recent(token) is user
    clock.advance(timedelta(microseconds=1))
    assert cache.recent(token) is None
    assert cache.recent(token) is None  # The expired entry was dropped.


def test_a_change_signalled_after_the_check_began_ends_reuse() -> None:
    clock = FakeClock(START)
    cache, signals = freshness(clock)
    token = claims()
    signals.publish(token.user_id)
    clock.advance(timedelta(seconds=1))
    cache.remember(token, SimpleNamespace(), clock.now())
    assert cache.recent(token) is not None  # The earlier change was already seen.
    signals.publish(token.user_id)
    assert cache.recent(token) is None


def test_a_change_during_the_database_read_is_not_missed() -> None:
    clock = FakeClock(START)
    cache, signals = freshness(clock)
    token = claims()
    began = clock.now()
    signals.publish(token.user_id)  # Committed while the check was reading.
    cache.remember(token, SimpleNamespace(), began)
    assert cache.recent(token) is None


def test_checks_are_keyed_by_family_and_security_version() -> None:
    clock = FakeClock(START)
    cache, _ = freshness(clock)
    token = claims()
    cache.remember(token, SimpleNamespace(), clock.now())
    assert cache.recent(claims(user_id=token.user_id, family_id=token.family_id)) is not None
    assert cache.recent(claims(user_id=token.user_id)) is None
    rotated = claims(user_id=token.user_id, family_id=token.family_id, security_version=2)
    assert cache.recent(rotated) is None


def test_an_older_check_never_replaces_a_newer_one_and_capacity_is_bounded() -> None:
    clock = FakeClock(START)
    cache, _ = freshness(clock, capacity=2)
    first, second, third = claims(), claims(), claims()
    newer = SimpleNamespace(name="newer")
    cache.remember(first, newer, clock.now())
    cache.remember(first, SimpleNamespace(name="older"), clock.now() - timedelta(seconds=5))
    assert cache.recent(first) is newer
    cache.remember(second, SimpleNamespace(), clock.now())
    cache.remember(third, SimpleNamespace(), clock.now())
    assert cache.recent(first) is None
    assert cache.recent(third) is not None


def test_invalid_configuration_is_refused() -> None:
    clock = FakeClock(START)
    with pytest.raises(ValueError, match="positive"):
        SessionFreshness(clock, InMemorySessionSignals(clock), timedelta(0))


def test_signals_notify_and_prune_by_retention_and_capacity() -> None:
    clock = FakeClock(START)
    woken: list[object] = []
    signals = InMemorySessionSignals(
        clock, notify=woken.append, retention=timedelta(minutes=1), capacity=2
    )
    first, second, third = uuid4(), uuid4(), uuid4()
    signals.publish(first)
    assert signals.changed_since(first, START)
    assert not signals.changed_since(first, START + timedelta(microseconds=1))
    clock.advance(timedelta(minutes=2))
    signals.publish(second)
    assert not signals.changed_since(first, START)  # Older than the retention window.
    signals.publish(third)
    signals.publish(first)
    assert not signals.changed_since(second, START)  # Evicted beyond capacity.
    assert woken == [first, second, third, first]

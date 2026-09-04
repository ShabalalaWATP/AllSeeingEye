"""Pure rules and infrastructure pieces tested in isolation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ase.adapters.links import PublicLinkBuilder
from ase.adapters.persistence.base import UTCDateTime
from ase.adapters.persistence.session import ensure_sqlite_directory, sqlite_path
from ase.adapters.security.hasher import Argon2PasswordHasher
from ase.adapters.security.tokens import SecretsTokenGenerator
from ase.domain.errors import WeakPassword
from ase.domain.lockout import LockoutPolicy
from ase.domain.password_policy import validate_password
from ase.domain.tokens import TokenPurpose
from ase.domain.users import Role, User, normalise_email
from ase.infrastructure.logging import redact_sensitive
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from helpers import FakeClock

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def make_user() -> User:
    return User(
        id=uuid4(),
        email="someone@example.com",
        display_name="Someone",
        role=Role.USER,
        is_active=True,
        password_hash="hash",
        failed_login_count=0,
        last_failed_at=None,
        locked_until=None,
        created_at=NOW,
        last_login_at=None,
    )


@pytest.mark.parametrize(
    ("password", "reason"),
    [
        ("short", "Use at least 12 characters."),
        ("x" * 129, "Use at most 128 characters."),
        ("Password1234", "This password is too common."),
        ("someone@example.com", "The password must not be your email address."),
        ("SOMEONE", None),
    ],
)
def test_password_policy(password: str, reason: str | None) -> None:
    if reason is None:
        # Too short anyway; the local-part rule is exercised with a long local part below.
        with pytest.raises(WeakPassword):
            validate_password(password, "someone@example.com")
        return
    with pytest.raises(WeakPassword) as excinfo:
        validate_password(password, "someone@example.com")
    assert excinfo.value.fields == {"new_password": reason}


def test_password_policy_accepts_good_passwords_and_rejects_local_part() -> None:
    validate_password("Correct-Horse-Battery-Staple", "someone@example.com")
    with pytest.raises(WeakPassword):
        validate_password("averylonglocalpart", "averylonglocalpart@example.com")


def test_lockout_policy_counts_within_window() -> None:
    policy = LockoutPolicy()
    user = make_user()
    for _ in range(4):
        assert policy.register_failure(user, NOW) is False
    assert policy.register_failure(user, NOW) is True
    assert user.is_locked(NOW)
    assert not user.can_log_in(NOW)
    assert user.can_log_in(NOW + timedelta(minutes=16))
    policy.register_success(user, NOW)
    assert user.locked_until is None
    assert user.last_login_at == NOW


def test_normalise_email() -> None:
    assert normalise_email("  Alex@Example.COM ") == "alex@example.com"


def test_links_are_url_safe() -> None:
    builder = PublicLinkBuilder("http://app.test/")
    assert (
        builder.link_for(TokenPurpose.ACTIVATION, "a b/c")
        == "http://app.test/activate?token=a%20b%2Fc"
    )
    assert builder.link_for(TokenPurpose.RESET, "x").startswith("http://app.test/reset-password?")


def test_token_generator_hashes_deterministically() -> None:
    generator = SecretsTokenGenerator()
    secret = generator.new_secret()
    assert len(secret) > 30
    assert generator.hash(secret) == generator.hash(secret)
    assert generator.hash(secret) != generator.hash(generator.new_secret())


def test_hasher_rejects_bad_hashes() -> None:
    hasher = Argon2PasswordHasher()
    digest = hasher.hash("Correct-Horse-Battery-Staple")
    assert hasher.verify(digest, "Correct-Horse-Battery-Staple")
    assert not hasher.verify(digest, "wrong")
    assert not hasher.verify("not-a-hash", "wrong")


def test_rate_limiter_windows_and_eviction() -> None:
    clock = FakeClock(NOW)
    limiter = InMemorySlidingWindowLimiter(clock, max_keys=2)
    assert limiter.hit("a", 2, 60) is None
    assert limiter.hit("a", 2, 60) is None
    assert limiter.hit("a", 2, 60) == 60
    clock.advance(timedelta(seconds=61))
    assert limiter.hit("a", 2, 60) is None
    limiter.hit("b", 1, 60)
    limiter.hit("c", 1, 60)
    assert limiter.hit("a", 2, 60) is None  # "a" was evicted and starts a fresh window
    limiter.reset()
    assert limiter.hit("b", 1, 60) is None


def test_redaction_processor() -> None:
    event = {
        "event": "login",
        "password": "hunter2",
        "Authorization": "Bearer x",
        "nested": {"token": "abc", "ok": 1},
        "plain": "keep",
    }
    redacted = redact_sensitive(None, "info", event)
    assert redacted["password"] == "[redacted]"
    assert redacted["Authorization"] == "[redacted]"
    assert redacted["nested"] == {"token": "[redacted]", "ok": 1}
    assert redacted["plain"] == "keep"


def test_utc_datetime_type_rejects_naive_values() -> None:
    column = UTCDateTime()
    with pytest.raises(ValueError, match="Naive"):
        column.process_bind_param(datetime(2026, 1, 1), None)  # type: ignore[arg-type]
    assert column.process_bind_param(None, None) is None  # type: ignore[arg-type]
    assert column.process_result_value(None, None) is None  # type: ignore[arg-type]
    restored = column.process_result_value(datetime(2026, 1, 1), None)  # type: ignore[arg-type]
    assert restored is not None
    assert restored.tzinfo is UTC


def test_sqlite_paths(tmp_path: object) -> None:
    assert sqlite_path("sqlite+aiosqlite://") is None
    assert sqlite_path("sqlite+aiosqlite:///:memory:") is None
    assert sqlite_path("postgresql+asyncpg://x") is None
    assert sqlite_path("sqlite+aiosqlite:///./data/ase.db") is not None
    ensure_sqlite_directory(f"sqlite+aiosqlite:///{tmp_path}/nested/dir/ase.db")
    ensure_sqlite_directory("postgresql+asyncpg://x")

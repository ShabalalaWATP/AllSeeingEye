"""Small MFA port doubles for deterministic security-race tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from ase.application.auth.mfa import MfaUseCase
from ase.application.auth.mfa_context import MfaContext
from ase.domain.mfa import MfaChallenge, MfaPurpose
from ase.domain.users import Role, User
from helpers import FakeClock

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def actor() -> User:
    return User(
        uuid4(),
        "owner@example.test",
        "Owner",
        Role.USER,
        True,
        "synthetic-hash",
        0,
        None,
        None,
        NOW,
        None,
    )


def challenge(user: User, *, enrol: bool = False) -> MfaChallenge:
    return MfaChallenge(
        "hash",
        user.id,
        user.security_version,
        MfaPurpose.LOGIN,
        NOW + timedelta(minutes=10),
        enrollment_required=enrol,
    )


def use_case(user: User, pending: MfaChallenge) -> MfaUseCase:
    repo = AsyncMock()
    repo.get.return_value = pending
    repo.email_enabled.return_value = False
    repo.save.return_value = True
    totp = AsyncMock()
    totp.get.return_value = None
    users = AsyncMock()
    users.lock_by_id.return_value = user
    hasher = Mock()
    hasher.verify.return_value = True
    limiter = Mock()
    limiter.hit.return_value = None
    email = Mock(available=True, send_code=AsyncMock(return_value=True))
    return MfaUseCase(
        MfaContext(
            repo,
            totp,
            Mock(available=True),
            users,
            hasher,
            Mock(),
            email,
            FakeClock(NOW),
            limiter,
            AsyncMock(),
            AsyncMock(),
            AsyncMock(),
            AsyncMock(),
            AsyncMock(),
        )
    )

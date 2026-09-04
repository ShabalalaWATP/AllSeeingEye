"""Account lockout rule: repeated failures within a window lock the account for a while."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class LockoutPolicy:
    max_failures: int = 5
    window: timedelta = timedelta(minutes=15)
    duration: timedelta = timedelta(minutes=15)

    def register_failure(self, user: User, now: datetime) -> bool:
        """Record a failed attempt. Returns True when this failure locks the account."""
        window_expired = user.last_failed_at is not None and now - user.last_failed_at > self.window
        if window_expired:
            user.failed_login_count = 0
        user.failed_login_count += 1
        user.last_failed_at = now
        if user.failed_login_count >= self.max_failures:
            user.locked_until = now + self.duration
            user.failed_login_count = 0
            return True
        return False

    def register_success(self, user: User, now: datetime) -> None:
        user.failed_login_count = 0
        user.last_failed_at = None
        user.locked_until = None
        user.last_login_at = now

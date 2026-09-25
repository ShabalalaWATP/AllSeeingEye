"""Recent authoritative session checks, so a release need not repeat the database read.

A check is reused only while it is younger than `max_age` and no committed session
change for that user has been signalled since it began. Changes made in this process
(logout, revocation, password, MFA, role or activation) end reuse at once; changes made
outside it, such as by a CLI or a direct database edit, are seen within `max_age`.
"""

from collections import OrderedDict
from datetime import datetime, timedelta
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.ports import Clock
from ase.application.ports.session import SessionSignals
from ase.domain.users import User

Key = tuple[UUID, UUID, int]


class SessionFreshness:
    def __init__(
        self,
        clock: Clock,
        signals: SessionSignals,
        max_age: timedelta,
        capacity: int = 4_096,
    ) -> None:
        if max_age <= timedelta(0) or capacity < 1:
            raise ValueError("Session freshness needs a positive age and capacity.")
        self._clock, self._signals = clock, signals
        self.max_age, self._capacity = max_age, capacity
        self._checks: OrderedDict[Key, tuple[User, datetime]] = OrderedDict()

    @staticmethod
    def _key(claims: AccessClaims) -> Key:
        return claims.user_id, claims.family_id, claims.security_version

    def recent(self, claims: AccessClaims) -> User | None:
        """The user from a still-trustworthy check of this session, or None to re-read."""
        key = self._key(claims)
        entry = self._checks.get(key)
        if entry is None:
            return None
        user, checked_at = entry
        if self.is_due(claims.user_id, checked_at):
            del self._checks[key]
            return None
        self._checks.move_to_end(key)
        return user

    def remember(self, claims: AccessClaims, user: User, checked_at: datetime) -> None:
        """Record a successful database check that began at `checked_at`."""
        key = self._key(claims)
        current = self._checks.get(key)
        if current is None or current[1] <= checked_at:
            self._checks[key] = (user, checked_at)
        self._checks.move_to_end(key)
        while len(self._checks) > self._capacity:
            self._checks.popitem(last=False)

    def is_due(self, user_id: UUID, checked_at: datetime) -> bool:
        """Whether a check that began at `checked_at` must be repeated before release."""
        expired = self._clock.now() - checked_at >= self.max_age
        return expired or self._signals.changed_since(user_id, checked_at)

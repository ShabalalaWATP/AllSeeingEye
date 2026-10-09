"""Server-owned idle deadlines shared by every consumer of a refresh family."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class SessionIdlePolicy:
    minutes: int = 180
    admin_minutes: int | None = None

    def duration(self, *, is_admin: bool) -> timedelta:
        minutes = (
            self.admin_minutes if is_admin and self.admin_minutes is not None else self.minutes
        )
        return timedelta(minutes=minutes)


@dataclass(frozen=True, slots=True)
class SessionActivity:
    server_now: datetime
    last_activity_at: datetime
    idle_expires_at: datetime
    idle_minutes: int

    @property
    def expired(self) -> bool:
        return self.server_now >= self.idle_expires_at

"""Public account-session metadata, never token material."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionSummary:
    id: UUID
    current: bool
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    user_agent: str | None
    ip: str | None


@dataclass(frozen=True, slots=True)
class SessionPage:
    items: list[SessionSummary]
    truncated: bool

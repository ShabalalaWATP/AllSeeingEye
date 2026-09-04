"""Wall clock in UTC. Tests substitute a fixed clock through the same port."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

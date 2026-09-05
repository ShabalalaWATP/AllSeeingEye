"""Per-source health and the circuit breaker that backs off failing feeds."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class SourceStatus(StrEnum):
    IDLE = "idle"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISABLED = "disabled"


@dataclass(slots=True)
class SourceHealth:
    source_id: str
    status: SourceStatus = SourceStatus.IDLE
    last_success: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    consecutive_failures: int = 0
    items_last_poll: int = 0
    last_latency_ms: float | None = None
    next_poll_at: datetime | None = None
    polls: int = 0


@dataclass(frozen=True, slots=True)
class CircuitBreaker:
    """Exponential backoff after failures; the source is disabled after too many in a row."""

    disable_after: int = 8
    base_backoff: timedelta = timedelta(seconds=60)
    max_backoff: timedelta = timedelta(hours=1)

    def backoff_for(self, consecutive_failures: int) -> timedelta:
        multiplier = int(2 ** min(20, max(0, consecutive_failures - 1)))
        backoff: timedelta = self.base_backoff * multiplier
        return min(backoff, self.max_backoff)

    def should_disable(self, consecutive_failures: int) -> bool:
        return consecutive_failures >= self.disable_after


@dataclass(slots=True)
class HealthRegistry:
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    _entries: dict[str, SourceHealth] = field(default_factory=dict)

    def get(self, source_id: str) -> SourceHealth:
        return self._entries.setdefault(source_id, SourceHealth(source_id=source_id))

    def snapshot(self) -> list[SourceHealth]:
        return sorted(self._entries.values(), key=lambda entry: entry.source_id)

    def record_success(
        self, source_id: str, items: int, latency_ms: float, now: datetime, interval: timedelta
    ) -> SourceHealth:
        entry = self.get(source_id)
        entry.status = SourceStatus.HEALTHY
        entry.last_success = now
        entry.consecutive_failures = 0
        entry.items_last_poll = items
        entry.last_latency_ms = latency_ms
        entry.polls += 1
        entry.next_poll_at = now + interval
        return entry

    def record_failure(self, source_id: str, error: str, now: datetime) -> SourceHealth:
        entry = self.get(source_id)
        entry.consecutive_failures += 1
        entry.last_error = error[:300]
        entry.last_error_at = now
        entry.polls += 1
        if self.breaker.should_disable(entry.consecutive_failures):
            entry.status = SourceStatus.DISABLED
            entry.next_poll_at = None
        else:
            entry.status = SourceStatus.DEGRADED
            entry.next_poll_at = now + self.breaker.backoff_for(entry.consecutive_failures)
        return entry

    def reset(self, source_id: str) -> SourceHealth:
        """An administrator re-enables a disabled source."""
        entry = self.get(source_id)
        entry.status = SourceStatus.IDLE
        entry.consecutive_failures = 0
        entry.next_poll_at = None
        return entry

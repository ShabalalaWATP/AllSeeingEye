"""Per-source health and the circuit breaker that backs off failing feeds."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

log = logging.getLogger(__name__)


class SourceStatus(StrEnum):
    IDLE = "idle"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISABLED = "disabled"


@dataclass(slots=True)
class SourceHealth:
    source_id: str
    status: SourceStatus = SourceStatus.IDLE
    status_reason: str | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    consecutive_failures: int = 0
    items_last_poll: int = 0
    last_latency_ms: float | None = None
    next_poll_at: datetime | None = None
    polls: int = 0
    # Fixed operator-facing text from FeedBlocked; cleared by any other outcome.
    blocked_reason: str | None = None
    # Current successful poll's coverage/quality caveat, separate from failure history.
    warning: str | None = None
    # Breaker trips since the last success or reset; each trip doubles the cool-down.
    trips: int = 0


@dataclass(frozen=True, slots=True)
class CircuitBreaker:
    """Exponential backoff after failures; too many in a row pause the source.

    A paused source is probed again after a cool-down that doubles on each trip
    without an intervening success. This never touches an administrator's source
    control switch, which alone keeps a feed off indefinitely.
    """

    disable_after: int = 8
    base_backoff: timedelta = timedelta(seconds=60)
    max_backoff: timedelta = timedelta(hours=1)
    cooldown: timedelta = timedelta(hours=6)
    max_cooldown: timedelta = timedelta(hours=24)

    def backoff_for(self, consecutive_failures: int) -> timedelta:
        multiplier = int(2 ** min(20, max(0, consecutive_failures - 1)))
        backoff: timedelta = self.base_backoff * multiplier
        return min(backoff, self.max_backoff)

    def cooldown_for(self, trips: int) -> timedelta:
        multiplier = int(2 ** min(20, max(0, trips - 1)))
        cooldown: timedelta = self.cooldown * multiplier
        return min(cooldown, self.max_cooldown)

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
        self,
        source_id: str,
        items: int,
        latency_ms: float,
        now: datetime,
        interval: timedelta,
        *,
        warning: str | None = None,
        coverage_warning: str | None = None,
    ) -> SourceHealth:
        entry = self.get(source_id)
        entry.blocked_reason = None
        self._transition(
            entry,
            SourceStatus.DEGRADED if warning else SourceStatus.HEALTHY,
            "poll_warning" if warning else "poll_succeeded",
        )
        if warning:
            entry.last_error, entry.last_error_at = warning[:300], now
        entry.warning = coverage_warning[:300] if coverage_warning else None
        entry.last_success = now
        entry.consecutive_failures = 0
        entry.trips = 0
        entry.items_last_poll = items
        entry.last_latency_ms = latency_ms
        entry.polls += 1
        entry.next_poll_at = now + interval
        return entry

    def record_deferred(
        self,
        source_id: str,
        error: str,
        now: datetime,
        retry_at: datetime,
        *,
        blocked: bool = False,
    ) -> SourceHealth:
        """A deliberate wait is not another failed upstream request."""
        entry = self.get(source_id)
        entry.blocked_reason = error[:300] if blocked else None
        entry.warning = None
        self._transition(
            entry, SourceStatus.DEGRADED, "provider_blocked" if blocked else "deferred"
        )
        entry.last_error, entry.last_error_at = error[:300], now
        entry.next_poll_at = retry_at
        entry.polls += 1
        return entry

    def record_failure(self, source_id: str, error: str, now: datetime) -> SourceHealth:
        entry = self.get(source_id)
        entry.warning = None
        entry.blocked_reason = None
        entry.consecutive_failures += 1
        entry.last_error = error[:300]
        entry.last_error_at = now
        entry.polls += 1
        if self.breaker.should_disable(entry.consecutive_failures):
            # Paused, not switched off: the scheduler probes again at next_poll_at.
            entry.trips += 1
            self._transition(entry, SourceStatus.DISABLED, "circuit_breaker")
            entry.next_poll_at = now + self.breaker.cooldown_for(entry.trips)
        else:
            self._transition(entry, SourceStatus.DEGRADED, "poll_failed")
            entry.next_poll_at = now + self.breaker.backoff_for(entry.consecutive_failures)
        return entry

    def record_rate_limited(
        self, source_id: str, error: str, now: datetime, retry_after: timedelta | None
    ) -> SourceHealth:
        """Back off at least as long as the upstream asked; a throttle never disables."""
        entry = self.get(source_id)
        entry.warning = None
        entry.blocked_reason = None
        entry.consecutive_failures += 1
        entry.last_error, entry.last_error_at = error[:300], now
        entry.polls += 1
        self._transition(entry, SourceStatus.DEGRADED, "rate_limited")
        wait = max(self.breaker.backoff_for(entry.consecutive_failures), retry_after or timedelta())
        entry.next_poll_at = now + min(wait, self.breaker.max_backoff)
        return entry

    def reset(self, source_id: str) -> SourceHealth:
        """An administrator resumes a paused source without waiting for its cool-down."""
        entry = self.get(source_id)
        entry.warning = None
        entry.blocked_reason = None
        self._transition(entry, SourceStatus.IDLE, "administrator_reset")
        entry.consecutive_failures = 0
        entry.trips = 0
        entry.next_poll_at = None
        return entry

    def administratively_disabled(self, source_id: str) -> None:
        self._transition(self.get(source_id), SourceStatus.DISABLED, "administrator_disabled")

    @staticmethod
    def _transition(entry: SourceHealth, status: SourceStatus, reason: str) -> None:
        if entry.status != status or (
            status is SourceStatus.DISABLED and entry.status_reason != reason
        ):
            log.info(
                "feed.health_transition",
                extra={
                    "source_id": entry.source_id,
                    "previous": entry.status.value,
                    "status": status.value,
                    "reason": reason,
                },
            )
        entry.status = status
        entry.status_reason = reason

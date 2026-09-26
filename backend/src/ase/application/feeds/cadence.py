"""When each feed polls: staggered first polls and the wait after every poll."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from ase.application.feeds.health import SourceHealth
from ase.domain.sources import SourceSpec

# Instrument feeds, the sensor layers that fill the live map, take the first
# quarter of the start-up window; every other feed spreads over the remainder.
MAP_CRITICAL_SHARE = 0.25
MIN_DELAY_SECONDS = 1.0


def first_poll_delay(spec: SourceSpec, spread: timedelta) -> float:
    """A start-up delay within uniform(0, min(interval, spread)), map layers first."""
    window = min(spec.poll_interval, spread).total_seconds()
    lead = window * MAP_CRITICAL_SHARE
    if spec.instrument:
        return random.uniform(0, lead)  # noqa: S311 # nosec B311
    return random.uniform(lead, window)  # noqa: S311 # nosec B311


def next_poll_delay(
    entry: SourceHealth, interval: timedelta, now: datetime, jitter: float
) -> float:
    """Honour a pending deadline (backoff, throttle or breaker cool-down), else the cadence."""
    delay = interval.total_seconds()
    # A deadline already passed belongs to an outcome that set no new one, such as a
    # source an administrator switched off. Keep the cadence rather than spinning.
    if entry.next_poll_at is not None and entry.next_poll_at > now:
        delay = max(MIN_DELAY_SECONDS, (entry.next_poll_at - now).total_seconds())
    # Jitter may spread work later, but must never advance a retry deadline.
    return delay * random.uniform(1, 1 + jitter)  # noqa: S311 # nosec B311

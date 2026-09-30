"""Transitions use fixed reasons and never log provider text."""

import logging
from datetime import UTC, datetime, timedelta

from ase.application.feeds.health import CircuitBreaker, HealthRegistry


def test_transition_failure_breaker_recovery_and_administrator_reasons(caplog):
    health = HealthRegistry(breaker=CircuitBreaker(disable_after=3))
    now = datetime.now(UTC)
    with caplog.at_level(logging.INFO):
        health.record_failure("test", "private-provider-error", now)
        health.record_failure("test", "private-provider-error", now)
        health.record_failure("test", "private-provider-error", now)
        health.record_failure("test", "private-provider-error", now)
        health.record_success("test", 0, 1, now, timedelta(seconds=60))
        health.administratively_disabled("test")
        health.administratively_disabled("test")
        health.reset("test")
    records = [
        record for record in caplog.records if record.getMessage() == "feed.health_transition"
    ]
    assert [record.reason for record in records] == [
        "poll_failed",
        "circuit_breaker",
        "poll_succeeded",
        "administrator_disabled",
        "administrator_reset",
    ]
    assert [record.status for record in records] == [
        "degraded",
        "disabled",
        "healthy",
        "disabled",
        "idle",
    ]
    assert "private-provider-error" not in caplog.text

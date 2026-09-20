"""Successful collection warnings must not inflate failure totals."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.adsb_global import AdsbGlobalConnector
from ase.adapters.feeds.http import FeedHttpStatusError
from ase.api.schemas_events import SourceHealthOut
from ase.application.feeds.health import HealthRegistry, SourceStatus
from feeds_helpers import NOW, FakeClock
from test_pipeline_and_scheduler import build_scheduler


def test_successful_limited_collection_preserves_warning_without_failure() -> None:
    registry = HealthRegistry()
    registry.record_failure("sampled", "An earlier failure", NOW - timedelta(minutes=2))
    entry = registry.record_success(
        "sampled", 12, 10.0, NOW, timedelta(minutes=2), coverage_warning="Limited sampled coverage"
    )
    assert entry.status is SourceStatus.HEALTHY
    assert entry.consecutive_failures == 0
    assert entry.last_success == NOW
    assert entry.items_last_poll == 12
    assert entry.next_poll_at == NOW + timedelta(minutes=2)
    assert entry.warning == "Limited sampled coverage"
    assert entry.last_error == "An earlier failure"
    assert entry.last_error_at == NOW - timedelta(minutes=2)
    assert SourceHealthOut.from_health(entry).warning == entry.warning


@pytest.mark.parametrize("outcome", ["success", "failure", "deferred", "limited", "reset"])
def test_warning_is_replaced_by_the_next_poll_outcome(outcome: str) -> None:
    registry = HealthRegistry()
    entry = registry.record_success(
        "sampled", 0, 10.0, NOW, timedelta(minutes=2), coverage_warning="x" * 500
    )
    assert len(entry.warning or "") == 300
    match outcome:
        case "success":
            registry.record_success("sampled", 0, 10.0, NOW, timedelta(minutes=2))
        case "failure":
            registry.record_failure("sampled", "failed", NOW)
        case "deferred":
            registry.record_deferred("sampled", "wait", NOW, NOW + timedelta(minutes=2))
        case "limited":
            registry.record_rate_limited("sampled", "throttled", NOW, timedelta(minutes=2))
        case "reset":
            registry.reset("sampled")
    assert entry.warning is None
    if outcome in {"failure", "limited"}:
        assert entry.status is SourceStatus.DEGRADED
        assert entry.consecutive_failures == 1


@pytest.mark.parametrize("partial_failure", [False, True])
async def test_scheduler_distinguishes_sampling_from_failed_sweep_requests(
    partial_failure: bool,
) -> None:
    clock, http = FakeClock(NOW), AsyncMock()
    payload = {"ac": [{"hex": "abcdef", "lat": 1, "lon": 2, "seen_pos": 3}]}
    http.get_json.side_effect = [
        FeedHttpStatusError(503, "https://provider.test") if partial_failure else payload,
        *[payload for _ in range(23)],
    ]
    connector = AdsbGlobalConnector(http, clock)
    connector._request_interval = 0
    scheduler, _, _, registry = build_scheduler([connector], clock)
    outcome = await scheduler.poll_once(connector)
    assert outcome.ok
    health = registry.get(connector.spec.id)
    assert health.warning and "Sampled worldwide sweep" in health.warning
    assert health.last_success == NOW and health.items_last_poll == 1
    if partial_failure:
        assert health.status is SourceStatus.DEGRADED
        assert health.last_error and "1 failed queries" in health.last_error
    else:
        assert health.status is SourceStatus.HEALTHY
        assert health.last_error is None

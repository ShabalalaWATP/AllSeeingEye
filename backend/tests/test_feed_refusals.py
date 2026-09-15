"""Publishers that refuse identified automated clients are deferred with a reason, not evaded."""

from __future__ import annotations

from datetime import timedelta

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.http_contracts import (
    FeedFetchError,
    FeedHttpStatusError,
    FeedTimeoutError,
)
from ase.adapters.feeds.rss_access import AUTOMATION_REFUSALS, REFUSAL_RECHECK
from ase.adapters.feeds.rss_sources import build_rss_connectors
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feed_diagnostics import FeedDeferred
from feeds_helpers import NOW, FakeClock


class FailingHttp:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.requests: list[str] = []

    async def get_text(self, url: str, *, conditional: bool = True) -> str:
        self.requests.append(url)
        raise self.error


def connector_for(source_id: str, error: Exception):
    http = FailingHttp(error)
    connectors = build_rss_connectors(http, FakeClock(NOW))  # type: ignore[arg-type]
    return next(c for c in connectors if c.spec.id == source_id), http


@pytest.mark.parametrize(
    ("source_id", "error"),
    [
        ("cyber_cisa_advisories", FeedHttpStatusError(403, "https://www.cisa.gov/x.xml")),
        ("cyber_acsc_advisories", FeedTimeoutError("Feed request exceeded its time limit.")),
        ("cyber_acsc_advisories", FeedFetchError("ReadError: Feed request failed.")),
    ],
)
async def test_known_refusal_is_deferred_with_an_operator_reason(source_id, error) -> None:
    connector, http = connector_for(source_id, error)
    with pytest.raises(FeedDeferred) as caught:
        await connector.fetch()
    assert str(caught.value) == AUTOMATION_REFUSALS[source_id]
    assert "imitate a browser" in str(caught.value)
    assert caught.value.retry_at == NOW + REFUSAL_RECHECK == NOW + timedelta(hours=12)
    assert len(http.requests) == 1  # the publisher is still asked, politely and rarely


@pytest.mark.parametrize(
    ("source_id", "error"),
    [
        ("cyber_cisa_advisories", FeedHttpStatusError(500, "https://www.cisa.gov/x.xml")),
        ("cyber_ncsc_news", FeedHttpStatusError(403, "https://www.ncsc.gov.uk/x.xml")),
    ],
)
async def test_other_failures_still_reach_the_circuit_breaker(source_id, error) -> None:
    connector, _ = connector_for(source_id, error)
    with pytest.raises(FeedHttpStatusError):
        await connector.fetch()


async def test_scheduler_shows_the_reason_without_counting_a_failure() -> None:
    connector, _ = connector_for(
        "cyber_cisa_advisories", FeedHttpStatusError(403, "https://www.cisa.gov/x.xml")
    )
    health = HealthRegistry()
    scheduler = FeedScheduler(
        [connector],
        Pipeline([Normaliser()]),
        InMemoryEventStore(),
        InMemoryEventBus(),
        health,
        FakeClock(NOW),
    )
    for _ in range(10):
        outcome = await scheduler.poll_once(connector)
    entry = health.get("cyber_cisa_advisories")
    assert not outcome.ok and entry.status is SourceStatus.DEGRADED
    assert entry.consecutive_failures == 0
    assert all(len(reason) <= 300 for reason in AUTOMATION_REFUSALS.values())  # health keeps 300
    assert entry.last_error == AUTOMATION_REFUSALS["cyber_cisa_advisories"]
    assert entry.next_poll_at == NOW + REFUSAL_RECHECK

"""CISA remediation guidance survives collection, store updates and Cyber snapshots."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit

import pytest

from ase.adapters.feeds.cisa_kev import SPEC, CisaKevConnector
from ase.adapters.feeds.kev_scores import KevScoreEnrichment
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.cyber import CyberService
from ase.application.feeds.health import HealthRegistry
from ase.domain.events import MAX_ATTRIBUTE_CHARS
from feeds_helpers import NOW, FakeClock, FakeHttp, load_fixture


async def collect(action):
    record = {**load_fixture("cisa_kev.json")["vulnerabilities"][0], "requiredAction": action}
    return (
        await CisaKevConnector(
            FakeHttp({"cisa.gov": {"vulnerabilities": [record]}}), FakeClock(NOW)
        ).fetch()
    )[0]


async def test_connector_required_action_survives_snapshot_and_changes_refresh_store() -> None:
    first = await collect("<p>Apply <b>vendor</b> mitigations.</p>")
    store = InMemoryEventStore()
    assert store.upsert((first,)).added == 1
    admission = SimpleNamespace(
        enabled_many=AsyncMock(side_effect=lambda ids: dict.fromkeys(ids, True))
    )
    service = CyberService(store, FakeClock(NOW), {SPEC.id: SPEC}, admission, HealthRegistry())
    initial = await service.release(await service.read())
    assert len(initial.items) == 1 and initial.items[0].kev is not None
    assert initial.items[0].kev.required_action == "Apply vendor mitigations."

    changed = await collect("Discontinue use if mitigations are unavailable.")
    assert changed.id == first.id and changed.content_hash != first.content_hash
    assert store.upsert((changed,)).updated == 1
    refreshed = await service.release(await service.read())
    assert len(refreshed.items) == 1 and refreshed.items[0].kev is not None
    assert refreshed.items[0].kev.required_action == (
        "Discontinue use if mitigations are unavailable."
    )


async def test_action_is_bounded_but_changes_beyond_retained_excerpt_refresh_hash() -> None:
    prefix = "Follow the vendor remediation instructions. " * 30
    first = await collect(prefix + "Original ending.")
    changed = await collect(prefix + "Revised ending.")
    assert len(first.attributes["required_action"]) <= MAX_ATTRIBUTE_CHARS
    assert first.attributes["required_action"] == changed.attributes["required_action"]
    assert first.content_hash != changed.content_hash


@pytest.mark.parametrize("action", [None, "", {}, 123])
async def test_missing_or_nontext_required_action_stays_unknown(action) -> None:
    event = await collect(action)
    assert event.attributes["required_action"] == ""


async def test_stalled_enrichment_does_not_discard_authoritative_cisa_records():
    catalogue = load_fixture("cisa_kev.json")
    http = AsyncMock()

    async def fetch(url, **kwargs):
        if url == SPEC.url:
            return catalogue
        assert urlsplit(url).hostname == "api.first.org"
        await asyncio.Event().wait()

    http.get_json.side_effect = fetch
    clock = FakeClock(NOW)
    scores = KevScoreEnrichment(http, clock, timeout_seconds=0.02)
    events = await CisaKevConnector(http, clock, scores).fetch()
    assert events
    assert all(event.source_id == SPEC.id for event in events)
    assert all("cve" in event.attributes for event in events)
    assert all("epss_probability" not in event.attributes for event in events)
    assert http.get_json.await_count == 2


async def test_late_catalogue_returns_records_without_optional_network(monkeypatch):
    times = iter((0.0, 56.0))
    monkeypatch.setattr("ase.adapters.feeds.cisa_kev.monotonic", lambda: next(times))
    http = AsyncMock()
    http.get_json.return_value = load_fixture("cisa_kev.json")
    clock = FakeClock(NOW)
    events = await CisaKevConnector(http, clock, KevScoreEnrichment(http, clock)).fetch()
    assert events
    assert all(event.source_id == SPEC.id for event in events)
    http.get_json.assert_awaited_once_with(SPEC.url)

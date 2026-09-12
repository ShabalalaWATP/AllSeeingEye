"""CISA remediation guidance survives collection, store updates and Cyber snapshots."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.cisa_kev import SPEC, CisaKevConnector
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

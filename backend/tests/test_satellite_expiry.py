"""An old orbital estimate must not survive the seven-day SPACE catalogue window."""

from datetime import timedelta

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.position_freshness import satellite_position_expired
from ase.domain.events import Category, freeze_attributes
from feeds_helpers import NOW, make_event


@pytest.mark.parametrize("value", ["bad", None, "2026-09-04T00:00:00Z", "2026-09-05T00:02:00Z"])
def test_invalid_or_stale_prediction_expires(value: str | None) -> None:
    event = make_event(category=Category.SPACE).with_changes(
        subtype="satellite",
        published_at=None,
        attributes=freeze_attributes({"position_at": value}),
    )
    assert satellite_position_expired(event, NOW)


def test_pruning_old_satellite_preserves_launches_and_fresh_predictions() -> None:
    satellite = make_event("sat", category=Category.SPACE).with_changes(subtype="satellite")
    launch = make_event("launch", category=Category.SPACE).with_changes(subtype="launch")
    current = satellite.with_changes(id="fresh", published_at=NOW + timedelta(minutes=10))
    store = InMemoryEventStore()
    store.upsert([satellite, launch, current])
    result = store.prune(NOW + timedelta(minutes=10, seconds=1))
    assert result.expired == 1
    assert satellite.id in result.ids
    assert store.get(launch.id) is not None
    assert store.get(current.id) is not None


def test_explicit_prediction_time_wins_over_recent_ingestion_and_boundary_is_retained() -> None:
    event = make_event(category=Category.SPACE).with_changes(
        subtype="satellite",
        attributes=freeze_attributes({"position_at": "2026-09-04T23:50:00"}),
    )
    assert not satellite_position_expired(event, NOW)
    assert satellite_position_expired(event, NOW + timedelta(seconds=1))

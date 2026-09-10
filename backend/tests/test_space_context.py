"""Space context must preserve unavailable scales and use the registered NOAA sources."""

from datetime import timedelta

import pytest

from ase.adapters.feeds.swpc import SwpcScalesConnector
from ase.container import Container
from ase.domain.events import Category
from feeds_helpers import NOW, FakeClock, FakeHttp, make_event


@pytest.mark.parametrize("value", [None, "", "unknown", "6", -1, False, {}, []])
async def test_unavailable_scale_is_not_reported_as_zero(value: object) -> None:
    payload = {"0": {"R": {"Scale": value}, "S": None, "G": "invalid"}}
    events = await SwpcScalesConnector(
        FakeHttp({"noaa-scales.json": payload}),
        FakeClock(NOW),  # type: ignore[arg-type]
    ).fetch()
    assert len(events) == 1
    event = events[0]
    assert event.attributes["r"] is None
    assert event.attributes["s"] is None
    assert event.attributes["g"] is None
    assert event.severity is None
    assert "unknown" in event.title
    assert "unavailable" in event.summary


async def test_explicit_zero_and_partial_scales_preserve_the_source_stamp() -> None:
    payload = {
        "0": {
            "DateStamp": "2026-09-04",
            "TimeStamp": "23:19:00",
            "R": {"Scale": 0, "Text": "none"},
            "S": {"Scale": "5", "Text": "extreme"},
        }
    }
    events = await SwpcScalesConnector(
        FakeHttp({"noaa-scales.json": payload}),
        FakeClock(NOW),  # type: ignore[arg-type]
    ).fetch()
    event = events[0]
    assert event.attributes["r"] == "0"
    assert event.attributes["s"] == "5"
    assert event.attributes["g"] is None
    assert event.attributes["stamp"] == "2026-09-04 23:19:00"
    assert event.published_at == NOW - timedelta(minutes=41)
    assert event.severity == 1.0


def test_space_board_counts_real_noaa_bulletins_but_not_scales(container: Container) -> None:
    now = container.clock.now()
    events = [
        make_event(
            source,
            source_id=source,
            category=Category.SPACE,
            subtype=subtype,
            point=None,
            published_at=now,
            observed_at=now,
        )
        for source, subtype in (
            ("noaa_swpc_alerts", "space_weather_alert"),
            ("noaa_swpc_scales", "space_weather_scales"),
            ("swpc_kp", "geomagnetic"),
            ("swpc_fake", "space_weather_alert"),
        )
    ]
    container.store.upsert(events)
    board = container.modules().space_board()
    assert board.alerts_24h == 1
    assert [event.source_id for event in board.latest_alerts] == ["noaa_swpc_alerts"]

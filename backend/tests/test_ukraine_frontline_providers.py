"""Frontline provider retries, malformed payloads and three-dimensional positions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ase.adapters.feeds.ukraine_frontline import (
    DEEPSTATE_COOLDOWN,
    FAILURE_RETRY,
    OCHA_COOLDOWN,
    FrontlineProviders,
    parse_deepstate,
    parse_ocha,
)
from ase.domain.ukraine.frontline import FrontlineStatus
from feeds_helpers import FakeClock, FakeHttp

NOW = datetime(2026, 9, 13, 12, tzinfo=UTC)
POLYGON = [[[37.0, 48.0, 0.0], [37.1, 48.0], [37.1, 48.1], [37.0, 48.0]]]
DEEPSTATE = {
    "datetime": "12.09 o 21:04",
    "map": {
        "features": [
            {
                "properties": {"name": "Occupied /// geoJSON.status.occupied"},
                "geometry": {"type": "Polygon", "coordinates": POLYGON},
            }
        ]
    },
}
OCHA = {
    "features": [
        {
            "properties": {"date": 1788912000000},
            "geometry": {
                "type": "LineString",
                "coordinates": [[37.0, 48.0, 12.5], [37.2, 48.3, 0.0]],
            },
        },
        {
            "properties": {},
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [[[36.0, 47.0, 1.0], [36.1, 47.1, 2.0]]],
            },
        },
        {"geometry": {"type": "LineString", "coordinates": [[37.0], [37.2, 48.3]]}},
        {"geometry": {"type": "LineString", "coordinates": [["37.0", 48.0], [37.2, 48.3]]}},
        {"geometry": {"type": "LineString", "coordinates": [[True, 48.0], [37.2, 48.3]]}},
    ]
}


def test_ocha_accepts_positions_with_altitude_and_skips_short_or_non_numeric_ones() -> None:
    assessed, features = parse_ocha(OCHA)
    assert assessed is not None
    assert features[0].lines == (((37.0, 48.0), (37.2, 48.3)), ((36.0, 47.0), (36.1, 47.1)))
    assert parse_ocha({"features": ["junk", {"geometry": "junk"}]}) == (None, ())


def test_deepstate_skips_non_dict_features_geometries_and_bad_rings() -> None:
    payload = {
        "map": {
            "features": [
                "junk",
                7,
                {"properties": "junk", "geometry": []},
                {
                    "properties": {"name": "geoJSON.status.occupied"},
                    "geometry": "Polygon",
                },
                {
                    "properties": {"name": "geoJSON.status.occupied"},
                    "geometry": {"type": "MultiPolygon", "coordinates": [[[[37.0]]]]},
                },
                *DEEPSTATE["map"]["features"],  # type: ignore[index]
            ]
        }
    }
    _, features = parse_deepstate(payload)
    assert len(features) == 1
    assert features[0].polygons[0][0][0] == (37.0, 48.0)


async def test_malformed_payload_is_unavailable_not_a_server_error() -> None:
    http = FakeHttp({"deepstatemap": {"map": {"features": "junk"}}})
    providers = FrontlineProviders(http, FakeClock(NOW), deepstate=True, ocha=False, spotted=False)  # type: ignore[arg-type]
    state = await providers.snapshot()
    assert state.status is FrontlineStatus.UNAVAILABLE

    class Exploding(FakeHttp):
        async def get_json(self, url: str, *, conditional: bool = True) -> object:
            raise AttributeError("'str' object has no attribute 'get'")

    broken = FrontlineProviders(
        Exploding(),  # type: ignore[arg-type]
        FakeClock(NOW),
        deepstate=False,
        ocha=True,
        spotted=True,
    )
    state = await broken.snapshot()
    assert state.status is FrontlineStatus.UNAVAILABLE and "attribute" not in state.reason
    assert (await broken.spotted()).status is FrontlineStatus.UNAVAILABLE


async def test_failures_retry_after_a_short_backoff_and_keep_the_last_good_snapshot() -> None:
    clock = FakeClock(NOW)
    http = FakeHttp()
    providers = FrontlineProviders(http, clock, deepstate=False, ocha=True, spotted=True)  # type: ignore[arg-type]
    assert (await providers.snapshot()).status is FrontlineStatus.UNAVAILABLE
    assert (await providers.snapshot()).status is FrontlineStatus.UNAVAILABLE
    assert len(http.requests) == 1
    assert (await providers.spotted()).status is FrontlineStatus.UNAVAILABLE
    assert len(http.requests) == 2  # the first month failed, so the second was never asked

    clock.advance(FAILURE_RETRY)
    http.payloads = {"unocha": OCHA}
    ready = await providers.snapshot()
    assert ready.status is FrontlineStatus.READY and ready.snapshot is not None
    assert len(http.requests) == 3

    # A good snapshot holds for the long provider cooldown.
    clock.advance(OCHA_COOLDOWN - timedelta(seconds=1))
    assert await providers.snapshot() is ready
    assert len(http.requests) == 3

    clock.advance(timedelta(seconds=1))
    http.payloads = {}
    stale = await providers.snapshot()
    assert stale.status is FrontlineStatus.STALE and stale.snapshot is ready.snapshot
    assert len(http.requests) == 4
    clock.advance(FAILURE_RETRY - timedelta(seconds=1))
    assert await providers.snapshot() is stale
    clock.advance(timedelta(seconds=1))
    http.payloads = {"unocha": OCHA}
    assert (await providers.snapshot()).status is FrontlineStatus.READY
    assert len(http.requests) == 5


async def test_deepstate_and_spotted_use_the_same_retry_rule() -> None:
    clock = FakeClock(NOW)
    http = FakeHttp({"deepstatemap": DEEPSTATE})
    providers = FrontlineProviders(http, clock, deepstate=True, ocha=False, spotted=True)  # type: ignore[arg-type]
    assert (await providers.snapshot()).status is FrontlineStatus.READY
    losses = {"losses": []}
    assert (await providers.spotted()).status is FrontlineStatus.UNAVAILABLE
    requests = len(http.requests)
    clock.advance(FAILURE_RETRY)
    http.payloads = {"deepstatemap": DEEPSTATE, "warspotting": losses}
    assert (await providers.spotted()).status is FrontlineStatus.READY
    assert len(http.requests) == requests + 1
    clock.advance(DEEPSTATE_COOLDOWN - FAILURE_RETRY - timedelta(seconds=1))
    await providers.snapshot()
    assert len(http.requests) == requests + 1


async def test_repeated_loss_ids_are_counted_once() -> None:
    """The provider repeats entries between calls, so identical ids must collapse."""
    row = {
        "id": 7,
        "type": "Tanks",
        "model": "T-80BVM",
        "status": "Destroyed",
        "lost_by": "Russia",
        "date": "2026-09-12",
        "nearest_location": "Lyman",
        "geo": "49.0,37.8",
    }
    http = FakeHttp({"warspotting": {"losses": [row, dict(row), {**row, "id": 8}]}})
    providers = FrontlineProviders(http, FakeClock(NOW), deepstate=False, ocha=False, spotted=True)  # type: ignore[arg-type]
    state = await providers.spotted()
    assert [loss.id for loss in state.losses] == [7, 8]
    assert len(http.requests) == 1

"""Sparse ADS-B altitude fields must not imply an airborne state."""

import pytest

from ase.adapters.feeds.adsb import SPEC, aircraft_event
from feeds_helpers import NOW


@pytest.mark.parametrize(
    ("altitude", "ground", "feet", "prefix"),
    [
        ("ground", True, None, "On the ground"),
        (0, False, 0.0, "Airborne at 0 ft"),
        (-100, False, -100.0, "Airborne at -100 ft"),
        (123.5, False, 123.5, "Airborne at 123 ft"),
        (None, None, None, "Ground status unknown"),
        ("", None, None, "Ground status unknown"),
        ("unknown", None, None, "Ground status unknown"),
        ("0", None, None, "Ground status unknown"),
        (True, None, None, "Ground status unknown"),
        (False, None, None, "Ground status unknown"),
        ({}, None, None, "Ground status unknown"),
        ([], None, None, "Ground status unknown"),
        (float("nan"), None, None, "Ground status unknown"),
        (float("inf"), None, None, "Ground status unknown"),
    ],
)
def test_altitude_preserves_ground_airborne_and_unknown(
    altitude: object, ground: bool | None, feet: float | None, prefix: str
) -> None:
    event = aircraft_event(
        SPEC,
        {"hex": "ae4e0e", "lat": 50, "lon": 10, "alt_baro": altitude},
        NOW,
        subtype="aircraft",
        tags=frozenset(),
    )
    assert event is not None
    assert event.attributes["on_ground"] is ground
    assert event.attributes["altitude_ft"] == feet
    assert event.summary is not None and event.summary.startswith(prefix)


def test_missing_altitude_does_not_use_speed_or_geometric_altitude_to_infer_ground_state() -> None:
    event = aircraft_event(
        SPEC,
        {"hex": "ae4e0e", "lat": 50, "lon": 10, "alt_geom": 1000, "gs": 200},
        NOW,
        subtype="aircraft",
        tags=frozenset(),
    )
    assert event is not None
    assert event.attributes["on_ground"] is None
    assert event.attributes["altitude_ft"] is None
    assert event.summary is not None and event.summary.startswith("Ground status unknown, 200 kt")

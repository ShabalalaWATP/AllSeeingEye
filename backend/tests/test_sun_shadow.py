"""The sun's position and the shadow it casts, against known astronomy."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from ase.domain.sun_shadow import (
    check_shadow,
    elevation_from_shadow,
    shadow_from_elevation,
    solar_position,
)


def test_equinox_noon_on_the_equator_puts_the_sun_overhead() -> None:
    # 20 March 2026, solar noon at Greenwich longitude 0 is close to 12:07 UTC.
    sun = solar_position(datetime(2026, 3, 20, 12, 7, tzinfo=UTC), 0.0, 0.0)
    assert sun.elevation_deg > 89.0
    assert abs(sun.declination_deg) < 0.5


def test_midsummer_noon_in_london_matches_the_almanac() -> None:
    # Solar noon in London on 21 June is about 13:02 BST (12:02 UTC); the sun is at 61.9 degrees.
    sun = solar_position(datetime(2026, 6, 21, 12, 2, tzinfo=UTC), 51.5074, -0.1278)
    assert 61.0 < sun.elevation_deg < 62.8
    assert 175 < sun.azimuth_deg < 185
    assert 23.3 < sun.declination_deg < 23.5


def test_afternoon_sun_is_in_the_west_and_night_is_below_the_horizon() -> None:
    afternoon = solar_position(datetime(2026, 6, 21, 16, 0, tzinfo=UTC), 51.5074, -0.1278)
    assert 240 < afternoon.azimuth_deg < 280 and afternoon.elevation_deg > 30
    night = solar_position(datetime(2026, 6, 21, 1, 0, tzinfo=UTC), 51.5074, -0.1278)
    assert night.elevation_deg < 0


def test_offsets_are_honoured_and_naive_times_refused() -> None:
    kyiv = timezone(timedelta(hours=3))
    local = solar_position(datetime(2026, 6, 21, 15, 2, tzinfo=kyiv), 51.5074, -0.1278)
    utc = solar_position(datetime(2026, 6, 21, 12, 2, tzinfo=UTC), 51.5074, -0.1278)
    assert local == utc
    with pytest.raises(ValueError, match="UTC offset"):
        solar_position(datetime(2026, 6, 21, 12, 2), 51.5, 0.0)
    with pytest.raises(ValueError, match="out of range"):
        solar_position(datetime(2026, 6, 21, 12, 2, tzinfo=UTC), 91.0, 0.0)


def test_shadow_and_elevation_are_inverses() -> None:
    assert elevation_from_shadow(1.0) == pytest.approx(45.0)
    assert shadow_from_elevation(45.0) == pytest.approx(1.0)
    assert shadow_from_elevation(0.0) is None
    with pytest.raises(ValueError):
        elevation_from_shadow(0.0)


def test_check_shadow_agrees_disagrees_and_notices_night() -> None:
    at = datetime(2026, 6, 21, 12, 2, tzinfo=UTC)
    # London at midsummer noon: the sun at ~62 degrees casts shadows ~0.53 times height.
    consistent = check_shadow(at, 51.5074, -0.1278, 0.55)
    assert consistent.status == "consistent" and consistent.expected_shadow == pytest.approx(
        0.53, abs=0.02
    )
    assert consistent.difference_deg is not None and consistent.difference_deg < 2
    # A shadow three times the object's height means a sun ~18 degrees up: not London at noon.
    inconsistent = check_shadow(at, 51.5074, -0.1278, 3.0)
    assert inconsistent.status == "inconsistent"
    # Sydney at 12:02 UTC is the middle of the night.
    night = check_shadow(at, -33.87, 151.21, 1.0)
    assert night.status == "sun_below_horizon" and night.expected_shadow is None

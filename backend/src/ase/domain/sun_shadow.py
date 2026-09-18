"""Where the sun was, and how long a shadow it cast, for a place and an instant.

A photograph that shows a vertical object and its shadow fixes the sun's height above the
horizon: shadow length divided by object height is the cotangent of the sun's elevation.
For a known capture instant that elevation is different at every point on Earth, so a
candidate location either agrees with the shadow or it does not. This is the reasoning
behind Bellingcat's ShadowFinder, written here from the NOAA solar position equations so
it needs no network and no dependency. It is an independent check on a candidate, never a
locator on its own: a shadow alone is consistent with a whole band of the globe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

#: A shadow estimated by eye from a photograph is coarse; the check allows this much
#: difference in sun elevation before calling a candidate inconsistent.
DEFAULT_TOLERANCE_DEG = 8.0
MIN_SHADOW_RATIO = 0.02
MAX_SHADOW_RATIO = 50.0


@dataclass(frozen=True, slots=True)
class SolarPosition:
    elevation_deg: float
    azimuth_deg: float
    declination_deg: float


def _require_instant(at: datetime) -> datetime:
    if at.utcoffset() is None:
        raise ValueError("The capture instant must carry a UTC offset")
    return at.astimezone(UTC)


def solar_position(at: datetime, latitude: float, longitude: float) -> SolarPosition:
    """The sun's elevation and azimuth (degrees, azimuth clockwise from north) at a place."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Latitude or longitude out of range")
    instant = _require_instant(at)
    julian_day = 2440587.5 + instant.timestamp() / 86400
    century = (julian_day - 2451545.0) / 36525
    mean_longitude = (280.46646 + century * (36000.76983 + century * 0.0003032)) % 360
    mean_anomaly = 357.52911 + century * (35999.05029 - 0.0001537 * century)
    eccentricity = 0.016708634 - century * (0.000042037 + 0.0000001267 * century)
    anomaly = math.radians(mean_anomaly)
    centre = (
        math.sin(anomaly) * (1.914602 - century * (0.004817 + 0.000014 * century))
        + math.sin(2 * anomaly) * (0.019993 - 0.000101 * century)
        + math.sin(3 * anomaly) * 0.000289
    )
    true_longitude = mean_longitude + centre
    omega = math.radians(125.04 - 1934.136 * century)
    apparent_longitude = math.radians(true_longitude - 0.00569 - 0.00478 * math.sin(omega))
    mean_obliquity = (
        23
        + (26 + (21.448 - century * (46.815 + century * (0.00059 - century * 0.001813))) / 60) / 60
    )
    obliquity = math.radians(mean_obliquity + 0.00256 * math.cos(omega))
    declination = math.asin(math.sin(obliquity) * math.sin(apparent_longitude))
    y = math.tan(obliquity / 2) ** 2
    l0 = math.radians(mean_longitude)
    equation_of_time = 4 * math.degrees(
        y * math.sin(2 * l0)
        - 2 * eccentricity * math.sin(anomaly)
        + 4 * eccentricity * y * math.sin(anomaly) * math.cos(2 * l0)
        - 0.5 * y * y * math.sin(4 * l0)
        - 1.25 * eccentricity * eccentricity * math.sin(2 * anomaly)
    )
    minutes = instant.hour * 60 + instant.minute + instant.second / 60
    true_solar_time = (minutes + equation_of_time + 4 * longitude) % 1440
    hour_angle = true_solar_time / 4 - 180
    if hour_angle < -180:
        hour_angle += 360
    lat, ha = math.radians(latitude), math.radians(hour_angle)
    cos_zenith = math.sin(lat) * math.sin(declination) + math.cos(lat) * math.cos(
        declination
    ) * math.cos(ha)
    zenith = math.acos(max(-1.0, min(1.0, cos_zenith)))
    elevation = 90 - math.degrees(zenith)
    if math.sin(zenith) < 1e-9 or abs(math.cos(lat)) < 1e-9:
        azimuth = 180.0 if latitude >= 0 else 0.0
    else:
        cos_az = (math.sin(lat) * math.cos(zenith) - math.sin(declination)) / (
            math.cos(lat) * math.sin(zenith)
        )
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
        azimuth = (angle + 180) % 360 if hour_angle > 0 else (540 - angle) % 360
    return SolarPosition(
        round(elevation, 2), round(azimuth, 2), round(math.degrees(declination), 4)
    )


def elevation_from_shadow(shadow_to_height: float) -> float:
    """The sun elevation, in degrees, that casts a shadow this many times the object's height."""
    if not MIN_SHADOW_RATIO <= shadow_to_height <= MAX_SHADOW_RATIO:
        raise ValueError("Shadow ratio out of range")
    return math.degrees(math.atan(1 / shadow_to_height))


def shadow_from_elevation(elevation_deg: float) -> float | None:
    """Shadow length as a multiple of object height for a sun this high; None below the horizon."""
    if elevation_deg <= 0.5:
        return None
    return 1 / math.tan(math.radians(elevation_deg))


@dataclass(frozen=True, slots=True)
class ShadowCheck:
    status: str  # consistent, inconsistent or sun_below_horizon
    sun: SolarPosition
    expected_shadow: float | None
    observed_shadow: float
    difference_deg: float | None
    tolerance_deg: float


def check_shadow(
    at: datetime,
    latitude: float,
    longitude: float,
    shadow_to_height: float,
    *,
    tolerance_deg: float = DEFAULT_TOLERANCE_DEG,
) -> ShadowCheck:
    """Does a shadow of this length agree with the sun at this place and instant?"""
    observed_elevation = elevation_from_shadow(shadow_to_height)
    sun = solar_position(at, latitude, longitude)
    expected = shadow_from_elevation(sun.elevation_deg)
    if expected is None:
        return ShadowCheck("sun_below_horizon", sun, None, shadow_to_height, None, tolerance_deg)
    difference = abs(sun.elevation_deg - observed_elevation)
    status = "consistent" if difference <= tolerance_deg else "inconsistent"
    return ShadowCheck(
        status, sun, round(expected, 2), shadow_to_height, round(difference, 1), tolerance_deg
    )

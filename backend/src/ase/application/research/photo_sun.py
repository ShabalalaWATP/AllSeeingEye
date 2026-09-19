"""Test each photo candidate against the sun, when the model saw a shadow and the time is known.

The vision model reports the shadows it can see as a length relative to the object casting
them. With a capture instant from the person who uploaded the photograph, the sun's height
at each candidate location is fixed, and a candidate either casts a shadow of that length
or it does not. The check is arithmetic on the model's own estimate: it can rule a candidate
out, it cannot confirm one, and a wrong capture time makes every result wrong, which is why
each check repeats the instant it was computed for.
"""

from __future__ import annotations

from datetime import datetime

from ase.domain.photo_geolocation import PhotoAssessment, SunShadowCheck
from ase.domain.sun_shadow import MAX_SHADOW_RATIO, MIN_SHADOW_RATIO, check_shadow

MAX_CHECKS = 18


def _note(status: str, sun_elevation: float, expected: float | None, observed: float) -> str:
    if status == "sun_below_horizon":
        return (
            f"At this time the sun would be below the horizon here (elevation "
            f"{sun_elevation:.0f} degrees), so no shadow of this kind could be cast. Either the "
            "place or the stated time is wrong."
        )
    if expected is None:
        return "The sun check could not be computed."
    if status == "consistent":
        return (
            f"The sun would stand about {sun_elevation:.0f} degrees above the horizon here, "
            f"casting shadows about {expected:.1f} times object height; the photograph shows "
            f"about {observed:.1f}. Consistent, which does not confirm the place."
        )
    return (
        f"The sun would stand about {sun_elevation:.0f} degrees above the horizon here, "
        f"casting shadows about {expected:.1f} times object height, but the photograph shows "
        f"about {observed:.1f}. The place, the time or the shadow estimate is wrong."
    )


def sun_checks(assessment: PhotoAssessment, captured_at: datetime | None) -> list[SunShadowCheck]:
    """One check per candidate with coordinates and per shadow the model reported."""
    if captured_at is None or captured_at.utcoffset() is None:
        return []
    checks: list[SunShadowCheck] = []
    for candidate in assessment.candidates:
        for shadow in assessment.shadows:
            if len(checks) >= MAX_CHECKS:
                return checks
            ratio = shadow.shadow_length_to_height
            if not MIN_SHADOW_RATIO <= ratio <= MAX_SHADOW_RATIO:
                continue
            if candidate.coordinates is None:
                checks.append(
                    SunShadowCheck(
                        candidate_label=candidate.label,
                        photo_id=shadow.photo_id,
                        status="no_coordinates",
                        captured_at=captured_at,
                        sun_elevation_deg=None,
                        sun_azimuth_deg=None,
                        expected_shadow_ratio=None,
                        observed_shadow_ratio=ratio,
                        note="This candidate has no coordinates, so the sun cannot be checked.",
                    )
                )
                continue
            result = check_shadow(
                captured_at, candidate.coordinates.latitude, candidate.coordinates.longitude, ratio
            )
            checks.append(
                SunShadowCheck(
                    candidate_label=candidate.label,
                    photo_id=shadow.photo_id,
                    status=result.status,
                    captured_at=captured_at,
                    sun_elevation_deg=result.sun.elevation_deg,
                    sun_azimuth_deg=result.sun.azimuth_deg,
                    expected_shadow_ratio=result.expected_shadow,
                    observed_shadow_ratio=ratio,
                    note=_note(
                        result.status, result.sun.elevation_deg, result.expected_shadow, ratio
                    ),
                )
            )
    return checks

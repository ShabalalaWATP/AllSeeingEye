"""Candidates are tested against the sun only when a shadow and a capture instant exist."""

from datetime import UTC, datetime

from ase.application.research.photo_sun import MAX_CHECKS, sun_checks
from ase.domain.photo_geolocation import (
    PhotoAssessment,
    PhotoCandidate,
    PhotoCoordinates,
    PhotoShadow,
)

NOON = datetime(2026, 6, 21, 12, 2, tzinfo=UTC)


def candidate(label: str, lat: float | None, lon: float | None) -> PhotoCandidate:
    return PhotoCandidate(
        label=label,
        country_iso=None,
        precision="city",
        supporting_clues=["A clue"],
        contradictions=[],
        coordinates=None
        if lat is None or lon is None
        else PhotoCoordinates(
            latitude=lat, longitude=lon, uncertainty_radius_km=5, basis="A named public feature"
        ),
    )


def assessment(*candidates: PhotoCandidate, ratio: float | None = 0.55) -> PhotoAssessment:
    return PhotoAssessment(
        status="candidates" if candidates else "unknown",
        summary="Test",
        visual_clues=[],
        candidates=list(candidates),
        verification_steps=["Check"],
        limitations=["Test"],
        shadows=[]
        if ratio is None
        else [
            PhotoShadow(
                photo_id="photo-1",
                shadow_length_to_height=ratio,
                basis="A lamp post and its shadow on level tarmac",
            )
        ],
    )


def test_each_candidate_gets_a_verdict_in_plain_words() -> None:
    checks = sun_checks(
        assessment(
            candidate("London", 51.5074, -0.1278),
            candidate("Sydney", -33.87, 151.21),
            candidate("Somewhere", None, None),
        ),
        NOON,
    )
    assert [check.status for check in checks] == [
        "consistent",
        "sun_below_horizon",
        "no_coordinates",
    ]
    london = checks[0]
    assert london.candidate_label == "London" and london.photo_id == "photo-1"
    assert london.captured_at == NOON and london.sun_elevation_deg is not None
    assert 61 < london.sun_elevation_deg < 63
    assert "Consistent, which does not confirm the place." in london.note
    assert "below the horizon" in checks[1].note
    assert checks[2].sun_elevation_deg is None and "no coordinates" in checks[2].note
    assert "0.6" in london.note or "0.5" in london.note


def test_inconsistent_shadow_says_which_things_could_be_wrong() -> None:
    (check,) = sun_checks(assessment(candidate("London", 51.5074, -0.1278), ratio=3.0), NOON)
    assert check.status == "inconsistent"
    assert "The place, the time or the shadow estimate is wrong." in check.note


def test_no_time_no_shadow_or_naive_time_means_no_checks() -> None:
    london = candidate("London", 51.5074, -0.1278)
    assert sun_checks(assessment(london), None) == []
    assert sun_checks(assessment(london, ratio=None), NOON) == []
    assert sun_checks(assessment(london), NOON.replace(tzinfo=None)) == []


def test_checks_are_bounded() -> None:
    many = assessment(*(candidate(f"Place {n}", 10.0, 10.0) for n in range(3)))
    many = many.model_copy(update={"shadows": many.shadows * 6})
    many = many.model_copy(update={"candidates": many.candidates * 3})
    assert len(sun_checks(many, NOON)) == MAX_CHECKS

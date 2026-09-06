"""Saved map state preserves versioned filters and rejects malformed/expensive input."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from ase.domain import map_topology
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.map_view_records import (
    canonical_state,
    revision_bytes,
    revision_digest,
    state_from_dict,
    state_to_dict,
)
from ase.domain.map_views import MapCamera, MapOverlay, MapViewState


def geometry(kind="Point", coordinates=None):
    return parse_map_geometry(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": kind,
                            "coordinates": [179, 89] if coordinates is None else coordinates,
                        },
                        "properties": {"label": "研究区域"},
                    }
                ],
            }
        )
    )


def state():
    return MapViewState(
        camera=MapCamera(179, 89, 4, 35, 40),
        source_ids=("fixture",),
        published_since=datetime(2026, 9, 1, tzinfo=UTC),
        published_until=datetime(2026, 9, 6, tzinfo=UTC),
        selected_evidence="E1",
        overlays=(
            MapOverlay(
                geometry(),
                "Declared source",
                date(2026, 9, 1),
                "Operator attribution",
                "approximate",
            ),
        ),
    )


def test_round_trip_preserves_polar_camera_labels_filters_and_independent_values():
    original = state()
    raw = state_to_dict(original)
    restored = state_from_dict(json.loads(json.dumps(raw)))
    assert restored == original
    raw["camera"]["latitude"] = 0
    raw["overlays"][0]["geometry"]["features"][0]["properties"]["label"] = "changed"
    assert restored.camera.latitude == 89
    assert "研究区域" in canonical_state(restored)


def test_digest_binds_title_report_version_evidence_and_state():
    original = state()
    digest = revision_digest(original, "Title", "version-1", "evidence-1")
    assert len(digest) == 64
    assert digest != revision_digest(original, "Other", "version-1", "evidence-1")
    assert digest != revision_digest(original, "Title", "version-2", "evidence-1")
    assert digest != revision_digest(original, "Title", "version-1", "evidence-2")
    assert digest != revision_digest(
        replace(original, projection="mercator"), "Title", "version-1", "evidence-1"
    )
    assert revision_bytes(original, "Title") > len(canonical_state(original).encode())


@pytest.mark.parametrize(
    "field,value",
    [
        ("projection", []),
        ("basemap", {}),
        ("basemap", "https://invalid.test/tiles"),
        ("schema_version", True),
        ("schema_version", 2),
        ("display_transform", "unknown"),
        ("include_unknown_dates", "yes"),
        ("selected_evidence", ""),
        ("source_ids", ["a", "a"]),
        ("source_ids", [None]),
        ("source_ids", "a"),
        ("source_ids", [str(index) for index in range(65)]),
        ("published_since", "2026-09-01"),
        ("published_until", False),
        ("published_until", "2026-01-01T00:00:00Z"),
        ("overlays", {}),
    ],
)
def test_invalid_state_json_is_rejected(field, value):
    raw = state_to_dict(state())
    raw[field] = value
    with pytest.raises(ValueError):
        state_from_dict(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("longitude", 10**400),
        ("longitude", True),
        ("longitude", 181),
        ("latitude", -91),
        ("zoom", -1),
        ("zoom", float("nan")),
        ("bearing", float("inf")),
        ("pitch", 61),
        ("pitch", []),
    ],
)
def test_invalid_camera_is_rejected_without_overflow_or_type_errors(field, value):
    raw = state_to_dict(state())
    raw["camera"][field] = value
    with pytest.raises(ValueError):
        state_from_dict(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", ""),
        ("source", "a\nsecret"),
        ("attribution", "a" * 501),
        ("precision", []),
        ("precision", "verified"),
        ("visible", 1),
        ("dataset_date", 1),
        ("dataset_date", "2026-13-01"),
    ],
)
def test_invalid_overlay_metadata_is_rejected(field, value):
    raw = state_to_dict(state())
    raw["overlays"][0][field] = value
    with pytest.raises(ValueError):
        state_from_dict(raw)


def test_unknown_fields_and_deep_payloads_are_safe_validation_failures():
    raw = state_to_dict(state())
    raw["scope"] = "other-team"
    with pytest.raises(ValueError):
        state_from_dict(raw)
    raw.pop("scope")
    nested = []
    for _ in range(1500):
        nested = [nested]
    raw["overlays"][0]["geometry"] = nested
    with pytest.raises(ValueError):
        state_from_dict(raw)


def test_aoi_requires_one_polygon_and_shares_topology_budget_across_overlays(monkeypatch):
    square = geometry("Polygon", [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]])
    assert state_from_dict(state_to_dict(replace(state(), aoi=square))).aoi == square
    with pytest.raises(ValueError):
        replace(state(), aoi=geometry())
    overlay = replace(state().overlays[0], geometry=square)
    raw = state_to_dict(replace(state(), overlays=(overlay,), aoi=square))
    monkeypatch.setattr(map_topology, "MAX_TOPOLOGY_CHECKS", 6)
    with pytest.raises(ValueError, match="Simplify"):
        state_from_dict(raw)


def test_equivalent_timezone_cutoffs_have_identical_canonical_state():
    original = state()
    offset = timezone(timedelta(hours=2))
    equivalent = replace(original, published_since=original.published_since.astimezone(offset))
    assert canonical_state(original) == canonical_state(equivalent)


@pytest.mark.parametrize("field,value", [("camera", {}), ("overlays", ({},)), ("aoi", {})])
def test_direct_state_construction_cannot_keep_mutable_unvalidated_values(field, value):
    with pytest.raises(ValueError):
        replace(state(), **{field: value})


def test_direct_overlay_requires_canonical_geometry():
    with pytest.raises(ValueError):
        replace(state().overlays[0], geometry={})


@pytest.mark.parametrize("cutoff", ["0001-01-01T00:00:00+01:00", "9999-12-31T23:30:00-01:00"])
def test_timezone_conversion_overflow_is_a_validation_error(cutoff):
    raw = state_to_dict(state())
    raw["published_since"] = cutoff
    raw["published_until"] = None
    with pytest.raises(ValueError, match="UTC date range"):
        state_from_dict(raw)

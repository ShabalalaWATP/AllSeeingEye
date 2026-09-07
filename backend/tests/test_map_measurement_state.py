"""Saved sketches preserve original coordinates and historical canonical contracts."""

import json
from dataclasses import FrozenInstanceError, replace

import pytest
from pydantic import ValidationError

from ase.api.schemas_map_views import MapStateFields
from ase.domain.map_measurement import METHOD, MapMeasurement, measurement_from_dict
from ase.domain.map_view_records import (
    canonical_state,
    revision_bytes,
    revision_digest,
    state_from_dict,
)
from ase.domain.map_views import MapCamera, MapViewState

LEGACY = (
    '{"aoi":null,"basemap":"dark","camera":{"bearing":0,"latitude":0,"longitude":0,'
    '"pitch":0,"zoom":4},"display_transform":"ase-geojson-display-v1",'
    '"include_unknown_dates":true,"overlays":[],"projection":"globe",'
    '"published_since":null,"published_until":null,"schema_version":1,'
    '"selected_evidence":null,"source_ids":[]}'
)


def test_absent_and_explicit_null_keep_legacy_bytes_and_revision_digest():
    for raw in (json.loads(LEGACY), {**json.loads(LEGACY), "measurement": None}):
        state = state_from_dict(raw)
        assert state.measurement is None
        assert canonical_state(state) == LEGACY
        assert revision_digest(state, "Legacy", "version-1", "evidence-1") == (
            "906eb988f5e52538e006ba7415199035378e5bd40c4666c754967b6ddbe9c1bb"
        )


@pytest.mark.parametrize("mode", ["distance", "area"])
@pytest.mark.parametrize("points", [[], [[179.123456789, 89]], [[180, 90], [-180, -90]] * 16])
def test_drafts_and_full_sketches_roundtrip_without_closing_reordering_or_rounding(mode, points):
    points = [list(point) for point in points]
    raw = {"mode": mode, "method": METHOD, "points": points}
    original = MapViewState(MapCamera(0, 0, 4), measurement=measurement_from_dict(raw))
    restored = state_from_dict(json.loads(canonical_state(original)))
    assert restored == original
    assert restored.measurement.points == tuple(tuple(point) for point in points)
    assert json.loads(canonical_state(restored))["measurement"] == raw
    assert revision_bytes(restored, "Sketch") > revision_bytes(
        replace(restored, measurement=None), "Sketch"
    )
    assert revision_digest(restored, "Sketch", "v1", "e1") != revision_digest(
        replace(restored, measurement=None), "Sketch", "v1", "e1"
    )
    points.append([0, 0])
    assert restored == original
    with pytest.raises(FrozenInstanceError):
        restored.measurement.mode = "area"


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "other"},
        {"mode": []},
        {"method": "future-version"},
        {"points": [[0, 0]] * 33},
        {"points": [[True, 0]]},
        {"points": [["1", 0]]},
        {"points": [[181, 0]]},
        {"points": [[0, -91]]},
        {"points": [[0, 0, 1]]},
        {"points": [[0]]},
        {"points": {}},
        {"points": [None]},
        {"points": [[float("nan"), 0]]},
        {"points": [[0, float("inf")]]},
        {"metres": 100},
        {"squareMetres": 100},
    ],
)
def test_storage_and_api_reject_invalid_or_client_asserted_measurements(change):
    raw = {"mode": "distance", "method": METHOD, "points": [[0, 0]], **change}
    with pytest.raises(ValueError):
        measurement_from_dict(raw)
    with pytest.raises(ValidationError):
        MapStateFields.model_validate(
            {"camera": {"longitude": 0, "latitude": 0, "zoom": 4}, "measurement": raw}
        )


@pytest.mark.parametrize("points", [[[0, 0]], ([0, 0],), ((False, 0),)])
def test_direct_domain_construction_cannot_retain_mutable_or_coerced_coordinates(points):
    with pytest.raises(ValueError):
        MapMeasurement("distance", points)
    with pytest.raises(ValueError):
        MapViewState(MapCamera(0, 0, 4), measurement={"points": points})

"""Map document imports reject arbitrary datasets and malformed geometry/terrain."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ase.domain.map_workspace import validate_payload

OBJECT = {
    "id": "one",
    "name": "Site",
    "shape": "point",
    "anchors": [[-1, 52]],
    "colour": "#abcdef",
    "visible": True,
    "locked": False,
    "notes": "",
}
TERRAIN = {
    "zoom": 10,
    "resolutionM": 30,
    "samples": [[-1, 52, 100], [-1.1, 52.1, None]],
    "profiles": [{"bearingDegrees": 90, "indices": [0, 1], "distancesM": [0, 1000]}],
}
RADIO = {
    "schemaVersion": 1,
    "savedAt": "2026-09-20T00:00:00Z",
    "draft": {
        "values": {"frequencyMHz": "150"},
        "presetId": "custom",
        "environment": {"radiusKm": "25"},
        "engineering": {"reserveDb": "10"},
        "antenna": {"enabled": True, "beamwidth": "90"},
    },
    "origin": [-1, 52],
    "receiver": None,
    "siteNames": {"origin": "TX", "receiver": "RX"},
    "result": {"kind": "terrain", "sampleCount": 2},
    "provenance": {"model": "Terrain screen", "terrainAttribution": None},
    "terrainEvidence": TERRAIN,
}


def test_saved_terrain_evidence_is_bounded_artefact_not_observation_history():
    validate_payload("radio", RADIO)


def test_actual_frontend_radio_snapshot_contract():
    fixture = Path(__file__).parents[2] / "frontend/src/test/fixtures/mapWorkspaceRadio.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    validate_payload("radio", payload)
    assert payload["terrainEvidence"]["profiles"][0]["bearingDegrees"] == 270


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("id", ""),
        ("name", "a" * 201),
        ("notes", "a" * 2001),
        ("shape", "building"),
        ("colour", "url(example)"),
        ("visible", 1),
        ("locked", None),
        ("anchors", [[0, 0]] * 33),
        ("anchors", [[0, 91]]),
        ("anchors", [[True, 0]]),
        ("anchors", [[0]]),
    ],
)
def test_drawing_field_bounds(key, value):
    obj = {**OBJECT, key: value}
    with pytest.raises(ValueError):
        validate_payload("drawings", {"version": 1, "objects": [obj]})


def test_drawing_duplicate_identity():
    with pytest.raises(ValueError, match="unique"):
        validate_payload("drawings", {"version": 1, "objects": [OBJECT, OBJECT]})


@pytest.mark.parametrize(
    "value",
    [
        {1: "value"},
        {"x": [0] * 2001},
        {"x": (1, 2)},
        {str(i): 0 for i in range(1001)},
        {str(i): [0] * 1000 for i in range(11)},
    ],
)
def test_json_structural_bounds(value):
    with pytest.raises(ValueError):
        validate_payload("radio", value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("schemaVersion", 2),
        ("schemaVersion", True),
        ("draft", {"events": []}),
        ("draft", {"values": {"frequencyMHz": ["150"]}}),
        ("draft", {"values": {"frequencyMHz": "1" * 101}}),
        ("draft", {"presetId": 5}),
        ("draft", {"antenna": {"enabled": "yes"}}),
        ("origin", [181, 0]),
        ("origin", [0, -91]),
        ("savedAt", {}),
        ("siteNames", {"origin": []}),
        ("result", {"status": "x" * 6001}),
        ("provenance", {"events": []}),
    ],
)
def test_radio_nested_bounds(key, value):
    with pytest.raises(ValueError):
        validate_payload("radio", {**RADIO, key: value})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("zoom", 23),
        ("resolutionM", 0),
        ("samples", [[-1, 52, 1]] * 1001),
        ("profiles", [{}] * 25),
        ("samples", [[0, 91, 1]]),
        ("samples", [[0, 0, 20000]]),
        ("profiles", [{"bearingDegrees": 361, "indices": [], "distancesM": []}]),
        ("profiles", [{"bearingDegrees": 90, "indices": [9], "distancesM": [0]}]),
        ("profiles", [{"bearingDegrees": 90, "indices": [0], "distancesM": [-1]}]),
        ("profiles", [{"bearingDegrees": 90, "indices": [0], "distancesM": []}]),
    ],
)
def test_terrain_sample_and_profile_integrity(key, value):
    payload = deepcopy(RADIO)
    payload["terrainEvidence"][key] = value
    with pytest.raises(ValueError):
        validate_payload("radio", payload)

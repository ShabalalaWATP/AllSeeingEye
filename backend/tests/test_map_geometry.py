"""Canonical map geometry rejects ambiguous input and bounds parsing and topology work."""

import hashlib
import json
import math

import pytest

from ase.domain import map_geometry, map_topology
from ase.domain.map_geometry import MAX_GEOJSON_BYTES, parse_map_geometry

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
HOLE = [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]


def feature(geometry, properties=None):
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def document(geometry, properties=None):
    return json.dumps({"type": "FeatureCollection", "features": [feature(geometry, properties)]})


def circle(count):
    points = [
        [math.cos(i * math.tau / count), math.sin(i * math.tau / count)] for i in range(count)
    ]
    return [*points, points[0]]


@pytest.mark.parametrize(
    ("geometry", "count"),
    [
        ({"type": "Point", "coordinates": [180, 90]}, 1),
        ({"type": "MultiPoint", "coordinates": [[1, 2], [3, 4]]}, 2),
        ({"type": "LineString", "coordinates": [[1, 2], [3, 4]]}, 2),
        ({"type": "MultiLineString", "coordinates": [[[1, 2], [3, 4]]]}, 2),
        ({"type": "Polygon", "coordinates": [SQUARE, HOLE]}, 10),
        ({"type": "MultiPolygon", "coordinates": [[SQUARE, HOLE], [SQUARE]]}, 15),
    ],
)
def test_supported_geometry_preserves_coordinates_and_round_trips(geometry, count):
    parsed = parse_map_geometry(document(geometry).encode())
    assert parsed.vertices == parsed.display_vertices == count
    assert parsed.feature_count == 1
    assert parsed.to_collection()["features"][0]["geometry"] == geometry
    assert parse_map_geometry(parsed.canonical_json) == parsed


def test_canonical_hash_and_ids_discard_extra_metadata_and_normalise_number_spelling():
    raw = {
        "type": "FeatureCollection",
        "url": "https://invalid.test/never-fetched",
        "features": [
            {
                **feature(
                    {"type": "Point", "coordinates": [-0.0, 1.0]},
                    {"name": "نام", "title": "ignored", "secret": "discarded"},
                ),
                "id": "private-id",
            },
            feature(
                {"type": "Point", "coordinates": [2, 3]}, {"title": "Title", "label": "ignored"}
            ),
            feature({"type": "Point", "coordinates": [4, 5]}, {"label": "Saved label"}),
            feature({"type": "Point", "coordinates": [6, 7]}, {"name": 3}),
        ],
    }
    parsed = parse_map_geometry(json.dumps(raw))
    collection = parsed.to_collection()
    assert [row["id"] for row in collection["features"]] == [0, 1, 2, 3]
    assert [row["properties"]["label"] for row in collection["features"]] == [
        "نام",
        "Title",
        "Saved label",
        "Feature 4",
    ]
    assert "secret" not in parsed.canonical_json and "private-id" not in parsed.canonical_json
    assert "invalid.test" not in parsed.canonical_json
    assert '"coordinates":[0,1]' in parsed.canonical_json
    assert parsed.sha256 == hashlib.sha256(parsed.canonical_json.encode()).hexdigest()
    collection["features"][0]["properties"]["label"] = "changed"
    assert parsed.to_collection()["features"][0]["properties"]["label"] == "نام"
    equivalent = json.loads(parsed.canonical_json)
    equivalent["features"][0]["geometry"]["coordinates"] = [0, 1.0]
    assert parse_map_geometry(json.dumps(equivalent, sort_keys=False)).sha256 == parsed.sha256


def test_label_limit_preserves_complete_unicode_codepoints():
    label = "a" * 299 + "🌐" + "discarded"
    parsed = parse_map_geometry(
        document({"type": "Point", "coordinates": [0, 0]}, {"label": label})
    )
    assert parsed.to_collection()["features"][0]["properties"]["label"] == label[:300]
    assert parse_map_geometry(parsed.canonical_json) == parsed


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        "\ud800",
        '{"type":"FeatureCollection","features":[],"ignored":"\\ud800"}',
        '{"type":"FeatureCollection","type":"FeatureCollection","features":[]}',
        '{"type":"FeatureCollection","features":[],"ignored":NaN}',
        '{"type":"FeatureCollection","features":[],"ignored":Infinity}',
        '{"type":"FeatureCollection","features":[],"ignored":-Infinity}',
        '{"type":"FeatureCollection","features":[],"ignored":1e9999}',
        '{"type":"FeatureCollection","features":[],"crs":null}',
        '{"type":"FeatureCollection","features":[],"ignored":{"crs":null}}',
        "[]",
        "null",
        "true",
        "{}",
        "{",
        '"unterminated',
        "]",
        "{]",
        "{} garbage",
    ],
)
def test_rejects_invalid_or_ambiguous_json_without_echoing_source(raw):
    with pytest.raises(ValueError):
        parse_map_geometry(raw)


def test_size_and_depth_are_checked_before_json_parser(monkeypatch):
    calls = 0
    original = json.loads

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(json, "loads", counted)
    for raw, message in [(b" " * (MAX_GEOJSON_BYTES + 1), "5 MiB"), ("[" * 17 + "]" * 17, "depth")]:
        with pytest.raises(ValueError, match=message):
            parse_map_geometry(raw)
    assert calls == 0


def test_depth_ignores_escaped_quotes_backslashes_and_brackets_in_strings():
    label = '[{\\"quoted"}]' * 8
    parsed = parse_map_geometry(
        document({"type": "Point", "coordinates": [0, 0]}, {"label": label})
    )
    assert parsed.to_collection()["features"][0]["properties"]["label"] == label


@pytest.mark.parametrize(
    "coordinates",
    [[True, 0], [0, False], ["0", 1], [0, None], [181, 0], [0, -91], [0, 0, 1], [0], [], None],
)
def test_rejects_invalid_positions_and_altitude(coordinates):
    with pytest.raises(ValueError):
        parse_map_geometry(document({"type": "Point", "coordinates": coordinates}))


@pytest.mark.parametrize(
    "geometry",
    [
        None,
        "https://invalid.test/geometry",
        {"type": "GeometryCollection", "geometries": []},
        {"type": "LineString", "coordinates": [[0, 0]]},
        {"type": "MultiPoint", "coordinates": []},
        {"type": "Polygon", "coordinates": []},
        {"type": "MultiPolygon", "coordinates": []},
    ],
)
def test_rejects_remote_null_and_unsupported_geometries(geometry):
    with pytest.raises(ValueError):
        parse_map_geometry(document(geometry))


def test_feature_collection_structure_and_limits():
    for raw in [
        {"type": "FeatureCollection", "features": []},
        {"type": "FeatureCollection", "features": [{"type": "Point"}]},
        {"type": "FeatureCollection", "features": [None]},
        {
            "type": "FeatureCollection",
            "features": [feature({"type": "Point", "coordinates": [0, 0]}, [])],
        },
        {
            "type": "FeatureCollection",
            "features": [feature({"type": "Point", "coordinates": [0, 0]})] * 2001,
        },
    ]:
        with pytest.raises(ValueError):
            parse_map_geometry(json.dumps(raw))
    maximum = {
        "type": "FeatureCollection",
        "features": [feature({"type": "Point", "coordinates": [0, 0]})] * 2000,
    }
    assert parse_map_geometry(json.dumps(maximum)).feature_count == 2000


@pytest.mark.parametrize(
    "rings",
    [
        [[[0, 0], [2, 0], [0, 1]]],
        [[[0, 0], [2, 0], [0, 1], [1, 1]]],
        [[[0, 0], [0, 0], [1, 1], [0, 0]]],
        [[[0, 0], [1, 0], [2, 0], [0, 0]]],
        [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
        [[[170, 0], [-170, 0], [-170, 10], [170, 0]]],
        [SQUARE, [[12, 12], [14, 12], [14, 14], [12, 14], [12, 12]]],
        [SQUARE, [[0, 2], [2, 2], [2, 4], [0, 4], [0, 2]]],
        [SQUARE, [[2, 2], [12, 2], [12, 4], [2, 4], [2, 2]]],
        [SQUARE, HOLE, [[2.5, 2.5], [3, 2.5], [3, 3], [2.5, 3], [2.5, 2.5]]],
        [SQUARE, HOLE, [[3, 1], [5, 1], [5, 3], [3, 3], [3, 1]]],
    ],
)
def test_rejects_unclosed_degenerate_intersecting_wrapped_or_invalid_hole_polygons(rings):
    with pytest.raises(ValueError):
        parse_map_geometry(document({"type": "Polygon", "coordinates": rings}))


def test_polygon_vertex_limit_includes_closure_and_all_holes():
    assert (
        parse_map_geometry(document({"type": "Polygon", "coordinates": [circle(255)]})).vertices
        == 256
    )
    with pytest.raises(ValueError, match="256"):
        parse_map_geometry(document({"type": "Polygon", "coordinates": [circle(256)]}))
    with pytest.raises(ValueError, match="256"):
        parse_map_geometry(document({"type": "Polygon", "coordinates": [circle(252), HOLE]}))


def test_shared_topology_budget_counts_edges_and_nonadjacent_segment_pairs(monkeypatch):
    assert map_topology.MAX_TOPOLOGY_CHECKS == 1_000_000
    monkeypatch.setattr(map_topology, "MAX_TOPOLOGY_CHECKS", 6)
    # One square charges4edges+2nonadjacent segment pairs, across one global counter.
    parse_map_geometry(document({"type": "Polygon", "coordinates": [SQUARE]}))
    with pytest.raises(ValueError, match="Simplify"):
        parse_map_geometry(document({"type": "MultiPolygon", "coordinates": [[SQUARE], [SQUARE]]}))


def test_hole_predicates_and_point_in_ring_are_charged_consistently(monkeypatch):
    # Two square rings:12checks, outer containment:5iterations, ring pairs:16checks.
    monkeypatch.setattr(map_topology, "MAX_TOPOLOGY_CHECKS", 33)
    parse_map_geometry(document({"type": "Polygon", "coordinates": [SQUARE, HOLE]}))
    monkeypatch.setattr(map_topology, "MAX_TOPOLOGY_CHECKS", 32)
    with pytest.raises(ValueError, match="Simplify"):
        parse_map_geometry(document({"type": "Polygon", "coordinates": [SQUARE, HOLE]}))


def test_real_whole_upload_topology_limit_rejects_many_individually_valid_polygons():
    geometry = {"type": "MultiPolygon", "coordinates": [[circle(255)]] * 40}
    with pytest.raises(ValueError, match=r"topology.*Simplify"):
        parse_map_geometry(document(geometry))


@pytest.mark.parametrize("coordinates", [[[180, 0], [-180, 1]], [[-180, 0], [180, 1]]])
def test_equal_wrapped_endpoints_do_not_add_display_seam_vertices(coordinates):
    parsed = parse_map_geometry(document({"type": "LineString", "coordinates": coordinates}))
    assert parsed.vertices == parsed.display_vertices == 2


def test_presplit_polygons_and_disjoint_holes_keep_original_coordinates():
    western = [[-180, 0], [-170, 0], [-170, 10], [-180, 10], [-180, 0]]
    eastern = [[170, 0], [180, 0], [180, 10], [170, 10], [170, 0]]
    second_hole = [[6, 6], [8, 6], [8, 8], [6, 8], [6, 6]]
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [[western], [eastern], [SQUARE, HOLE, second_hole]],
    }
    parsed = parse_map_geometry(document(geometry))
    assert parsed.to_collection()["features"][0]["geometry"] == geometry


def test_vertex_bound_is_global_and_canonical_line_coordinates_survive_seam_crossings():
    lines = {
        "type": "MultiLineString",
        "coordinates": [[[170, 10], [-170, 20]], [[180, 0], [-180, 1]]],
    }
    parsed = parse_map_geometry(document(lines))
    assert parsed.vertices == 4 and parsed.display_vertices == 6
    assert parsed.to_collection()["features"][0]["geometry"] == lines
    maximum = {"type": "MultiPoint", "coordinates": [[0, 0]] * 100000}
    assert parse_map_geometry(document(maximum)).vertices == 100000
    excessive = {"type": "MultiLineString", "coordinates": [[[0, 0]] * 60000, [[0, 0]] * 40001]}
    with pytest.raises(ValueError, match="100,000"):
        parse_map_geometry(document(excessive))
    seam_excess = {"type": "LineString", "coordinates": [[0, 0]] * 99998 + [[170, 0], [-170, 0]]}
    with pytest.raises(ValueError, match="display"):
        parse_map_geometry(document(seam_excess))


def test_canonical_serialisation_also_has_a_byte_limit(monkeypatch):
    # Absent properties expand into a deterministic label; count canonical bytes too.
    raw = (
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"geometry":{"type":"Point","coordinates":[0,0]}}]}'
    )
    monkeypatch.setattr(map_geometry, "MAX_GEOJSON_BYTES", len(raw.encode()))
    with pytest.raises(ValueError, match="Canonical"):
        parse_map_geometry(raw)

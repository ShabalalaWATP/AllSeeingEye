"""Original footprint preservation and legacy saved-map integrity contracts."""

import hashlib
import io
import json
import math
import zipfile
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.errors import InvalidRequest
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_geometry import (
    EvidenceGeometry,
    LocationRole,
    geometry_from_dict,
    geometry_to_dict,
)
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.observation import ObservationMetadata, observation_from_dict, observation_to_dict
from ase.domain.report_records import evidence_from_list, evidence_to_list
from feeds_helpers import NOW, make_event
from report_documents_helpers import document_records


def geometry(raw=None):
    if raw is None:
        ring = [[math.cos(i * math.tau / 300), math.sin(i * math.tau / 300)] for i in range(300)]
        raw = {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}
    return EvidenceGeometry(
        json.dumps(raw),
        LocationRole.OBSERVATION_FOOTPRINT,
        "reported_scene_boundary",
        "provider_coordinates",
        "catalogue",
        "Synthetic catalogue fixture",
    )


def snapshot(event):
    return EvidenceItem.from_event("E1", event, NOW, source_name="Source", independence_key="")


def test_legacy_evidence_digest_is_unchanged_by_absent_new_fields():
    item = snapshot(make_event())
    rows = evidence_to_list((item,))
    assert "geometry" not in rows[0] and "observation" not in rows[0]
    restored = evidence_from_list(json.loads(json.dumps(rows)))
    _, version = document_records()
    golden = "d7822238f359643a23983538fdfe052c6ff2ecb2b288d99f5f408cbc02783d1e"
    assert evidence_digest(replace(version, evidence=restored)) == golden
    archived = replace(restored[0], archive_url="https://example.org/archive")
    assert evidence_digest(replace(version, evidence=(archived,))) == golden


def test_large_source_footprint_survives_freezing_and_packages_without_a_centroid(monkeypatch):
    source = geometry()
    observation = ObservationMetadata(
        NOW - timedelta(days=2),
        "sentinel-fixture",
        "scene-1",
        "Scene metadata only",
        processed_at=NOW - timedelta(days=1),
        scene_cloud_cover=7.5,
    )
    event = make_event().with_changes(point=None, geometry=source, observation=observation)
    rows = evidence_to_list((snapshot(event),))
    restored = evidence_from_list(json.loads(json.dumps(rows)))
    assert restored[0].geometry == source
    assert restored[0].observation == observation
    assert restored[0].lon is restored[0].lat is None
    assert restored[0].published_at == event.published_at != observation.acquired_at
    collection = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": source.to_geometry()},
        ],
    }
    with pytest.raises(ValueError):
        parse_map_geometry(json.dumps(collection))  # Display limit must not truncate source data.
    record, version = document_records()
    version = replace(version, evidence=restored)
    renderer = FrozenEvidencePackageRenderer()
    with zipfile.ZipFile(io.BytesIO(renderer.render(record, version))) as archive:
        assert json.loads(archive.read("evidence.json")) == rows
        feature = json.loads(archive.read("evidence.geojson"))["features"][0]
        assert feature["geometry"] == source.to_geometry()
        assert feature["properties"]["geometry_sha256"] == source.sha256
        assert feature["properties"]["location_role"] == "observation_footprint"
        assert feature["properties"]["observation"] == observation_to_dict(observation)
        for entry in json.loads(archive.read("manifest.json"))["files"]:
            assert hashlib.sha256(archive.read(entry["path"])).hexdigest() == entry["sha256"]
        total = sum(info.file_size for info in archive.infolist())
    monkeypatch.setattr("ase.adapters.reports.evidence_package.MAX_PACKAGE_BYTES", total - 1)
    with pytest.raises(InvalidRequest, match="8 MiB"):
        renderer.render(record, version)


def test_private_store_accounts_for_source_geometry_and_observation_bytes():
    base = make_event()
    event = base.with_changes(
        geometry=geometry(),
        observation=ObservationMetadata(NOW, "collection", "item", "限制"),
    )
    assert estimate_bytes(event) > estimate_bytes(base) + len(
        event.geometry.source_geometry.encode()
    )
    store = InMemoryEventStore(memory_budget_bytes=estimate_bytes(event) - 1)
    store.upsert((event,))
    assert store.get(event.id) is None


def test_oversized_geometry_is_rejected_before_materialising_export_trees(monkeypatch):
    source = geometry()
    record, version = document_records()
    version = replace(version, evidence=(snapshot(make_event().with_changes(geometry=source)),))
    monkeypatch.setattr(
        "ase.adapters.reports.evidence_package.MAX_PACKAGE_BYTES",
        len(source.source_geometry.encode("utf-8")),
    )

    def forbidden_materialisation(*args):
        raise AssertionError("Oversized geometry must be rejected before building export trees")

    monkeypatch.setattr(
        "ase.adapters.reports.evidence_package.evidence_to_list", forbidden_materialisation
    )
    with pytest.raises(InvalidRequest, match="8 MiB"):
        FrozenEvidencePackageRenderer().render(record, version)


@pytest.mark.parametrize(
    "kind,coordinates",
    [
        ("Point", [1, 2]),
        ("MultiPoint", [[1, 2], [3, 4]]),
        ("LineString", [[179, 0], [-179, 0]]),
        ("MultiLineString", [[[1, 2], [3, 4]]]),
        ("Polygon", [[[0, 0], [1, 0], [0, 1], [0, 0]]]),
        ("MultiPolygon", [[[[0, 0], [1, 0], [0, 1], [0, 0]]]]),
    ],
)
def test_supported_geometry_roundtrip_preserves_coordinates(kind, coordinates):
    raw = {"type": kind, "coordinates": coordinates}
    item = geometry(raw)
    assert geometry_from_dict(geometry_to_dict(item)) == item
    assert item.to_geometry() == raw
    item.to_geometry()["coordinates"] = []
    assert item.to_geometry() == raw


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"type": "GeometryCollection", "coordinates": []},
        {"type": "Point", "coordinates": [True, 0]},
        {"type": "Point", "coordinates": [181, 0]},
        {"type": "Point", "coordinates": [10**500, 0]},
        {"type": "Point", "coordinates": [float("nan"), 0]},
        {"type": "Point", "coordinates": [0, 0, 1]},
        {"type": "LineString", "coordinates": [[0, 0]]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1], [1, 1]]]},
        {"type": "Point", "coordinates": [0, 0], "crs": "other"},
    ],
)
def test_invalid_source_geometry_is_rejected(raw):
    with pytest.raises(ValueError):
        geometry(raw)


def test_geometry_hash_tampering_and_structural_limits(monkeypatch):
    row = geometry_to_dict(geometry())
    with pytest.raises(ValueError, match="hash"):
        geometry_from_dict({**row, "sha256": "0" * 64})
    with pytest.raises(ValueError):
        geometry_from_dict({**row, "unexpected": True})
    monkeypatch.setattr("ase.domain.evidence_geometry.MAX_GEOMETRY_VERTICES", 300)
    with pytest.raises(ValueError):
        geometry()
    monkeypatch.setattr("ase.domain.evidence_geometry.MAX_GEOMETRY_BYTES", 20)
    with pytest.raises(ValueError):
        geometry({"type": "Point", "coordinates": [0, 0]})


@pytest.mark.parametrize(
    "changes",
    [
        {"acquired_at": None},
        {"acquired_at": NOW.replace(tzinfo=None)},
        {"processed_at": "yesterday"},
        {"scene_cloud_cover": True},
        {"scene_cloud_cover": float("nan")},
        {"scene_cloud_cover": 101},
        {"scene_cloud_cover": 10**500},
        {"collection_id": ""},
        {"limitations": "x" * 2001},
    ],
)
def test_observation_validation(changes):
    with pytest.raises(ValueError):
        ObservationMetadata(
            **{
                "acquired_at": NOW,
                "collection_id": "c",
                "item_id": "i",
                "limitations": "Unknown coverage",
                **changes,
            }
        )


def test_observation_roundtrip_and_invalid_frozen_data():
    value = ObservationMetadata(NOW, "collection", "item", "No imagery inspected")
    assert observation_from_dict(observation_to_dict(value)) == value
    assert observation_from_dict(None) is geometry_from_dict(None) is None
    with pytest.raises(ValueError):
        observation_from_dict({})
    with pytest.raises(ValueError):
        observation_from_dict({**observation_to_dict(value), "acquired_at": "bad"})

"""Original scene geometry survives catalogue normalisation and report encoding."""

import math
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pytest

from ase.adapters.research_records.copernicus import CopernicusFootprintProvider
from ase.adapters.research_records.copernicus_research import scene_event
from ase.domain.evidence import EvidenceItem
from ase.domain.footprints import FootprintQuery
from ase.domain.report_records import evidence_from_list, evidence_to_list
from test_copernicus_research import NOW, QUERY, RAW

CATALOGUE_QUERY = FootprintQuery((0, 0, 1, 1), QUERY.since, QUERY.until, True)


def payload(geometry=None):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "synthetic",
                "collection": "sentinel-2-l2a",
                "geometry": deepcopy(RAW if geometry is None else geometry),
                "properties": {"datetime": (NOW - timedelta(hours=1)).isoformat()},
            }
        ],
    }


def parse(data):
    return CopernicusFootprintProvider(None, SimpleNamespace(now=lambda: NOW))._parse(
        data,
        CATALOGUE_QUERY,
    )


@pytest.mark.parametrize("multipart", [False, True])
def test_original_type_coordinates_and_null_dates_survive_frozen_evidence(multipart):
    raw = {"type": "MultiPolygon", "coordinates": [RAW["coordinates"]]} if multipart else RAW
    result = parse(payload(raw))
    original = result.features[0].source_geometry
    assert original.to_geometry() == raw
    assert isinstance(original.to_geometry()["coordinates"][0][0][0], list if multipart else int)
    event = scene_event(result.features[0], NOW)
    item = EvidenceItem.from_event("E1", event, NOW, source_name="Catalogue", independence_key="")
    restored = evidence_from_list(evidence_to_list((item,)))[0]
    assert restored.geometry == original
    assert restored.published_at is None
    assert restored.observation.acquired_at == NOW - timedelta(hours=1)


def test_more_than_annotation_vertex_limit_is_preserved():
    ring = [
        [0.5 + 0.4 * math.cos(i * 2 * math.pi / 300), 0.5 + 0.4 * math.sin(i * 2 * math.pi / 300)]
        for i in range(300)
    ]
    ring.append(ring[0])
    raw = {"type": "Polygon", "coordinates": [ring]}
    result = parse(payload(raw))
    assert result.features[0].source_geometry.vertices == 301
    assert result.features[0].source_geometry.to_geometry() == raw


def test_inclusive_start_exclusive_end():
    data = payload()
    data["features"][0]["properties"]["datetime"] = QUERY.since.isoformat()
    assert len(parse(data).features) == 1
    data["features"][0]["properties"]["datetime"] = QUERY.until.isoformat()
    assert parse(data).status == "empty"


def test_extra_crs_is_rejected_without_rewriting_source_geometry():
    data = payload()
    data["features"][0]["geometry"]["crs"] = "untrusted"
    with pytest.raises(ValueError):
        parse(data)

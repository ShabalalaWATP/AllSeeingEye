"""Project intersection uses actual polygons, holes and bounded catalogue candidates."""

import json
from dataclasses import replace

import pytest

from ase.adapters.research_records.aiddata_catalogue import import_project_directory
from ase.adapters.research_records.aiddata_records import parse_project
from ase.adapters.research_records.aiddata_search import search_catalogue
from ase.adapters.research_records.project_spatial import ProjectSpatialFilter
from test_aiddata_records import source
from test_aiddata_search import END, START, catalogue
from test_research_area import area


def box(west, south, east, north):
    return [[west, south], [east, south], [east, north], [west, north], [west, south]]


def geometry(rings):
    original = parse_project(source(), expected_id="35756").geometry
    return replace(original, source_geometry=json.dumps({"type": "Polygon", "coordinates": rings}))


def test_hole_is_not_a_match_even_when_envelopes_overlap():
    target = ProjectSpatialFilter(area([box(2, 2, 3, 3)]))
    assert not target.intersects(geometry([box(0, 0, 5, 5), box(1, 1, 4, 4)]))
    assert target.intersects(geometry([box(0, 0, 5, 5)]))
    assert target.intersects(geometry([box(3, 3, 4, 4)]))
    assert not target.intersects(None)


def test_invalid_and_unsplit_geometry_fails_without_repair():
    target = ProjectSpatialFilter(area([box(0, 0, 1, 1)]))
    with pytest.raises(ValueError, match="valid"):
        target.intersects(geometry([[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]))
    with pytest.raises(ValueError, match="seam"):
        target.intersects(geometry([box(-179, 0, 179, 1)]))


def test_shared_geometry_budget_fails_before_further_intersection(monkeypatch):
    monkeypatch.setattr("ase.adapters.research_records.project_spatial.MAX_QUERY_VERTICES", 9)
    with pytest.raises(ValueError, match="work limit"):
        ProjectSpatialFilter(area([box(0, 0, 1, 1)])).intersects(geometry([box(0, 0, 1, 1)]))


def test_area_filter_searches_beyond_first_twenty_nonmatching_projects(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for number in range(22):
        identity = 35756 + number
        data = json.loads(source(id=identity))
        west = 50 if number == 21 else 0
        data["features"][0]["geometry"]["coordinates"] = [[box(west, 0, west + 1, 1)]]
        (inputs / f"{identity}.geojson").write_text(json.dumps(data), encoding="utf-8")
    path = import_project_directory(inputs, tmp_path / "cache")
    result = search_catalogue(
        path, terms=(), since=START, until=END, area=area([box(50, 0, 51, 1)])
    )
    assert [record.project.project_id for record in result.records] == ["35777"]
    assert not result.truncated


def test_final_spatial_predicate_cannot_release_results_after_deadline(tmp_path, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(
        "ase.adapters.research_records.aiddata_search.time.monotonic", lambda: clock[0]
    )

    def late(self, geometry):
        clock[0] = 3.0
        return True

    monkeypatch.setattr(ProjectSpatialFilter, "intersects", late)
    with pytest.raises(ValueError, match="work limit"):
        search_catalogue(
            catalogue(tmp_path), terms=(), since=START, until=END, area=area([box(0, 0, 1, 1)])
        )

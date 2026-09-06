"""Exact AOI preservation, explicit spatial admission and unchanged replan scope."""

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from ase.api.schemas_research_plan import ResearchPlanOut
from ase.application.research.collection import ResearchCollector
from ase.application.research.pacing import RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.research import CollectionStatus
from ase.domain.research_area import ResearchArea, area_from_dict, area_to_dict
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from test_research_plan import QUERY, Provider

RING = [[10, 40], [12, 40], [12, 42], [10, 42], [10, 40]]


def area(coordinates=None, *, kind="Polygon"):
    return ResearchArea(
        parse_map_geometry(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"label": "Operator area منطقة"},
                            "geometry": {"type": kind, "coordinates": coordinates or [RING]},
                        }
                    ],
                }
            )
        )
    )


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    async def wait(self):
        pass

    monkeypatch.setattr(RequestPacer, "wait", wait)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("start", range(4))
def test_rectangle_is_exact_independent_of_start_and_winding(reverse, start):
    corners = RING[:-1][::-1] if reverse else RING[:-1]
    rotated = corners[start:] + corners[:start]
    rectangle = area([[*rotated, rotated[0]]])
    assert rectangle.rectangle_bounds == (10, 40, 12, 42)
    assert area_from_dict(area_to_dict(rectangle)) == rectangle


@pytest.mark.parametrize(
    "coordinates,kind",
    [
        ([[[10, 40], [12, 41], [10, 42], [10, 40]]], "Polygon"),
        ([RING, [[10.5, 40.5], [11, 40.5], [11, 41], [10.5, 40.5]]], "Polygon"),
        ([[RING], [[[13, 40], [14, 40], [14, 41], [13, 40]]]], "MultiPolygon"),
        ([[[10, 40], [11, 40], [12, 40], [12, 42], [10, 42], [10, 40]]], "Polygon"),
        (
            [
                [[[179, 40], [180, 40], [180, 42], [179, 42], [179, 40]]],
                [[[-180, 40], [-179, 40], [-179, 42], [-180, 42], [-180, 40]]],
            ],
            "MultiPolygon",
        ),
    ],
)
def test_nonrectangular_holey_or_split_areas_never_become_bounding_envelopes(coordinates, kind):
    value = area(coordinates, kind=kind)
    assert value.rectangle_bounds is None
    assert area_from_dict(area_to_dict(value)) == value


def test_single_multipolygon_rectangle_and_boundary_coordinates():
    assert area([[RING]], kind="MultiPolygon").rectangle_bounds == (10, 40, 12, 42)
    assert area([[[178, 88], [180, 88], [180, 90], [178, 90], [178, 88]]]).rectangle_bounds == (
        178,
        88,
        180,
        90,
    )


@pytest.mark.parametrize("value", [None, {}, [], "polygon"])
def test_area_requires_immutable_canonical_geometry(value):
    with pytest.raises(ValueError, match="canonical geometry"):
        ResearchArea(value)


def test_rejects_points_multiple_features_and_forged_canonical_counters():
    point = parse_map_geometry(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10, 40]}}
                ],
            }
        )
    )
    with pytest.raises(ValueError, match="one polygon"):
        ResearchArea(point)
    collection = area().geometry.to_collection()
    collection["features"].append(collection["features"][0])
    with pytest.raises(ValueError, match="one polygon"):
        ResearchArea(parse_map_geometry(json.dumps(collection)))
    with pytest.raises(ValueError, match="inconsistent"):
        ResearchArea(replace(area().geometry, sha256="0" * 64))
    with pytest.raises(ValueError, match="immutable area"):
        replace(QUERY, area={})


@pytest.mark.parametrize(
    "malformed", [[], {}, {"geometry": {}}, {"geometry": {}, "sha256": "x", "url": "x"}]
)
def test_frozen_area_rejects_unknown_or_missing_fields(malformed):
    with pytest.raises(ValueError, match="Invalid frozen research area"):
        area_from_dict(malformed)


def test_hash_and_json_fail_closed_and_returned_geometry_is_independent():
    original = area()
    serialised = area_to_dict(original)
    serialised["geometry"]["features"][0]["geometry"]["coordinates"][0][0][0] = 11
    assert original.rectangle_bounds == (10, 40, 12, 42)
    serialised = area_to_dict(original)
    serialised["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        area_from_dict(serialised)
    with pytest.raises(ValueError, match="geometry"):
        area_from_dict({"geometry": {"invalid": float("nan")}, "sha256": "x"})
    assert area_from_dict(None) is None and area_to_dict(None) is None


async def test_legacy_country_support_cannot_admit_area_or_consume_request_budget():
    legacy = Provider("country-source")
    query = replace(QUERY, country_iso="GB", area=area())
    result = await ResearchCollector([legacy]).collect(query)
    assert legacy.queries == []
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert result.plan.area == query.area
    assert not result.plan.tasks[0].supported
    assert not result.plan.tasks[0].spatial_supported
    assert "does not establish support" in result.plan.tasks[0].spatial_scope
    await ResearchCollector([legacy]).collect(QUERY)
    assert legacy.queries == [QUERY]


class SpatialProvider(Provider):
    spatial_scope = "Exact rectangular area sent as native bbox; catalogue records only."

    def supports_area(self, query):
        return query.area is not None and query.area.rectangle_bounds is not None


async def test_capable_source_receives_exact_area_and_unsupported_shape_makes_no_request():
    provider = SpatialProvider("spatial")
    query = replace(QUERY, area=area())
    service = ResearchCollectionService(lambda _: [Provider("legacy"), provider])
    preview = service.plan(query)
    result = await service.collect(query)
    assert provider.queries == [query]
    assert result.plan == preview
    assert preview.tasks[1].spatial_supported and preview.tasks[1].supported
    assert preview.tasks[1].spatial_scope == provider.spatial_scope
    await service.collect(replace(query, area=area([[[10, 40], [12, 41], [10, 42], [10, 40]]])))
    assert provider.queries == [query]


@pytest.mark.parametrize("answer", [False, None, 1, "yes", "failure"])
async def test_capability_requires_explicit_true_and_never_leaks_failures(answer):
    class InvalidProvider(Provider):
        spatial_scope = "x" * 1001

        def supports_area(self, query):
            if answer == "failure":
                raise ValueError("private query and credentials")
            return answer

    provider = InvalidProvider("invalid")
    result = await ResearchCollector([provider]).collect(replace(QUERY, area=area()))
    assert provider.queries == []
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert "credentials" not in repr(result)
    assert len(result.plan.tasks[0].spatial_scope) < 1001


async def test_frozen_plan_and_api_preserve_geometry_hash_and_legacy_defaults():
    provider = SpatialProvider("spatial")
    query = replace(QUERY, area=area())
    result = await ResearchCollector([provider]).collect(query)
    receipt = ResearchReceipt.build(query, result.attempts, 0, result.plan)
    wire = research_to_dict(receipt)
    expected = area_to_dict(query.area)
    assert wire["plan"]["area"] == expected
    assert research_from_dict(json.loads(json.dumps(wire))) == receipt
    assert ResearchPlanOut.model_validate(result.plan).model_dump(mode="json")["area"] == expected
    wire["plan"]["area"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        research_from_dict(wire)
    with pytest.raises(ValidationError, match="hash"):
        ResearchPlanOut.model_validate(wire["plan"])
    old = research_to_dict(receipt)
    del old["plan"]["area"]
    for task in old["plan"]["tasks"]:
        del task["spatial_supported"], task["spatial_scope"]
    restored = research_from_dict(old)
    assert restored.plan.area is None and not restored.plan.tasks[0].spatial_supported


@pytest.mark.parametrize("change", ["remove", "replace", "terms_only"])
async def test_replan_cannot_remove_or_replace_the_area_and_each_pass_freezes_it(change):
    original_area = area()
    query = replace(QUERY, area=original_area)
    providers = [SpatialProvider(str(index)) for index in range(6)]

    async def replan(original, first, remaining):
        assert first.plan.area == original_area and remaining > 0
        candidate = replace(original, terms=("revised",))
        if change == "remove":
            return replace(candidate, area=None)
        if change == "replace":
            return replace(
                candidate, area=area([[[10, 41], [12, 41], [12, 43], [10, 43], [10, 41]]])
            )
        return candidate

    result = await ResearchCollectionService(lambda _: providers).collect(query, replan=replan)
    assert sum(len(provider.queries) for provider in providers) == 6
    assert all(value.area == original_area for provider in providers for value in provider.queries)
    if change != "terms_only":
        assert all(value == query for provider in providers for value in provider.queries)
    assert len(result.passes) == 2
    assert all(row.plan.area == original_area for row in result.passes)
    receipt = ResearchReceipt.build(query, result.attempts, 0, result.plan, result.passes)
    wire = research_to_dict(receipt)
    assert all(row["plan"]["area"] == area_to_dict(original_area) for row in wire["passes"])
    assert research_from_dict(json.loads(json.dumps(wire))) == receipt

"""The packaged register provider: what it reads, what it refuses, and what it never claims."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ase.adapters.geo import scope_geography as geography
from ase.adapters.geo.asset_registers import BY_COUNTRY, BY_OUTLINE, BY_PATH, scan_registers
from ase.adapters.research.asset_register import (
    NO_GEOGRAPHY_REASON,
    SCANNABLE,
    SOURCE_ID,
    AssetRegisterProvider,
)
from ase.domain.area_assets import NO_TRIGGER_REASON, AssetClass
from ase.domain.area_inventory import MAX_LISTED_ITEMS, RegisterEntry, RegisterItem, bound_entries
from ase.domain.events import GeoConfidence
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_area import direct_area_from_geometry

SINCE = datetime(2026, 9, 10, tzinfo=UTC)
UNTIL = SINCE + timedelta(days=5)


def box(west, south, east, north):
    return direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [west, south],
                                [east, south],
                                [east, north],
                                [west, north],
                                [west, south],
                            ]
                        ],
                    },
                }
            ],
        }
    )


DUBLIN = box(-6.55, 53.20, -5.95, 53.55)


def query(question="What is happening in this area?", **kwargs):
    return ResearchQuery(
        question=question,
        since=SINCE,
        until=UNTIL,
        mode=kwargs.pop("mode", ResearchMode.DETAILED),
        **kwargs,
    )


SNAPSHOT = {
    "data_centres": [
        {
            "id": "a",
            "name": "Alpha DC",
            "country": "IE",
            "longitude": -6.2,
            "latitude": 53.35,
            "precision": "site",
            "source_url": "https://example.test/a",
        },
        {
            "id": "b",
            "name": "Beta DC",
            "country": "FR",
            "longitude": 2.35,
            "latitude": 48.85,
            "precision": "city",
        },
    ],
    "data_centre_attribution": "OpenStreetMap contributors",
    "data_centre_snapshot_date": "2026-09-13",
    "data_centre_licence_url": "https://www.openstreetmap.org/copyright",
    "cables": [
        {"id": "c1", "name": "Alpha cable", "path": [[-6.4, 53.3], [-6.0, 53.4]]},
        {"id": "c2", "name": "Far cable", "path": [[20.0, 10.0], [21.0, 11.0]]},
    ],
    "cable_attribution": "OpenStreetMap contributors",
    "snapshot_date": "2026-09-08",
}


async def test_a_drawn_area_reads_every_register_and_names_only_a_few():
    result = await AssetRegisterProvider().collect(query(area=DUBLIN))
    assert result.attempts[0].status is CollectionStatus.COMPLETED
    assert {AssetClass(event.attributes["asset_class"]) for event in result.items} <= SCANNABLE
    for event in result.items:
        assert event.attributes["records_named"] <= MAX_LISTED_ITEMS
        cable = event.attributes["asset_class"] == "submarine_cables"
        assert event.attributes["matched_by"] == (BY_PATH if cable else BY_OUTLINE)
        assert event.attributes["scope_basis"] == "drawn_area"
        # A register summary is context about a place, never a located observation.
        assert event.point is None and event.geometry is None
        assert event.geo_confidence is GeoConfidence.NONE
        assert event.published_at is None and event.source_id == SOURCE_ID
        assert "not evidence of current state" in (event.summary or "")
    classes = {event.attributes["asset_class"] for event in result.items}
    assert {"data_centres", "submarine_cables"} <= classes


async def test_a_country_question_naming_an_asset_matches_the_declared_country_field():
    result = await AssetRegisterProvider().collect(
        query("What data centre capacity is present in Ireland?", country_isos=("IE",))
    )
    assert result.attempts[0].status is CollectionStatus.COMPLETED
    assert {event.attributes["asset_class"] for event in result.items} == {"data_centres"}
    event = result.items[0]
    assert event.attributes["matched_by"] == BY_COUNTRY
    assert event.attributes["scope_basis"] == "country_outline"
    assert event.country_iso == "IE" and event.attributes["records_in_scope"] > 0


@pytest.mark.parametrize(
    "question",
    (
        "Assess the outcome of the Dutch general election.",
        "What did the European Central Bank decide at its September meeting?",
        "Assess the Akira ransomware campaign in the latest CISA advisory.",
        "Assess the joint diplomatic statement after the summit.",
        "What is the current measles outbreak situation?",
        "What happened this week?",
    ),
)
async def test_ordinary_country_questions_read_no_register_at_all(question):
    provider = AssetRegisterProvider()
    request = query(question, country_isos=("IE",))
    assert provider.supports(request) is False
    result = await provider.collect(request)
    assert result.items == ()
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert result.attempts[0].explanation == NO_TRIGGER_REASON


async def test_a_named_asset_without_a_resolvable_geography_states_why_and_stops():
    provider = AssetRegisterProvider()
    request = query("Assess the risk to submarine cables worldwide.")
    assert provider.supports(request) is False
    result = await provider.collect(request)
    assert result.items == ()
    assert result.attempts[0].explanation == NO_GEOGRAPHY_REASON


async def test_an_unpackaged_country_code_degrades_with_a_stated_reason():
    result = await AssetRegisterProvider().collect(
        query("Assess the power grid and substations there.", country_isos=("MT",))
    )
    assert result.items == ()
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert result.attempts[0].explanation == NO_GEOGRAPHY_REASON


async def test_record_focused_research_never_reaches_the_registers():
    provider = AssetRegisterProvider()
    request = query(
        "Which data centres does this company run?",
        focus=ResearchFocus.COMPANY,
        subject="Example Ltd",
    )
    assert provider.supports(request) is False
    assert (await provider.collect(request)).items == ()


async def test_identity_and_content_hash_are_stable_for_the_same_scope():
    first = await AssetRegisterProvider().collect(query(area=DUBLIN))
    second = await AssetRegisterProvider().collect(query(area=DUBLIN, mode=ResearchMode.ADVANCED))
    assert [row.id for row in first.items] == [row.id for row in second.items]
    assert [row.content_hash for row in first.items] == [row.content_hash for row in second.items]


def test_the_scan_uses_exact_geometry_for_points_and_routes():
    scope = geography.from_area(DUBLIN)
    entries = scan_registers(frozenset(AssetClass), scope, snapshot=SNAPSHOT)
    by_class = {row.asset_class: row for row in entries}
    assert by_class["data_centres"].count == 1
    assert by_class["data_centres"].listed[0].name == "Alpha DC"
    assert by_class["submarine_cables"].count == 1
    assert by_class["submarine_cables"].matched_by == BY_PATH
    assert "OpenStreetMap" in by_class["data_centres"].provenance()


def test_country_scanning_uses_the_declared_country_field_not_the_coarse_outline():
    scope = geography.from_countries(("FR",))
    entries = scan_registers(
        frozenset({AssetClass.DATA_CENTRES}), scope, country_isos=("FR",), snapshot=SNAPSHOT
    )
    assert entries[0].count == 1 and entries[0].listed[0].name == "Beta DC"
    assert entries[0].matched_by == BY_COUNTRY


def test_entries_with_no_records_are_dropped_and_bounds_are_enforced():
    empty = RegisterEntry("x", "map:x", "X", 0, (), "2026-01-01", "a", "b")
    assert bound_entries((empty,)) == ()
    with pytest.raises(ValueError):
        RegisterEntry("x", "map:x", "X", 0, (RegisterItem("n", None, "site", None),), "d", "a", "b")
    with pytest.raises(ValueError):
        RegisterItem("n", None, "site", "http://insecure.test")
    entry = RegisterEntry(
        "x", "map:x", "X", 9, (RegisterItem("n", "IE", "site", None),), "2026-01-01", "a", "b"
    )
    assert entry.unlisted == 8 and "8 further record(s)" in entry.describe()


def test_a_country_outline_is_a_union_that_states_its_own_limitation():
    scope = geography.from_countries(("IE", "GB"))
    assert scope is not None
    assert "Natural Earth 1:110m" in scope.scope.limitation
    assert scope.contains_point(-6.26, 53.35) and not scope.contains_point(2.35, 48.85)
    assert geography.from_countries(("MT",)) is None
    assert geography.from_countries(()) is None


def test_a_conflict_box_is_labelled_a_collection_box_and_never_a_boundary():
    scope = geography.from_conflict_box(
        "ukraine", "Russia's war in Ukraine", (22.0, 44.0, 41.0, 52.5)
    )
    assert scope.scope.basis == "conflict_box"
    assert "not a conflict boundary" in scope.scope.limitation
    with pytest.raises(ValueError):
        geography.from_conflict_box("bad", "Bad", (41.0, 44.0, 22.0, 52.5))


def test_a_saved_area_keeps_its_own_basis_and_a_route_check_refuses_rubbish():
    scope = geography.from_area(DUBLIN, saved=True)
    assert scope.scope.basis == "saved_map_area"
    assert scope.crosses_path([[-6.4, 53.3], [-6.0, 53.4]]) is True
    assert scope.crosses_path([[-6.4, 53.3]]) is False
    assert scope.crosses_path([["x", "y"], ["a", "b"]]) is False
    assert scope.crosses_path([[0, 0]] * 5000) is False


def test_supports_is_cheap_and_does_not_depend_on_the_interval():
    provider = AssetRegisterProvider()
    asked = query("Assess the undersea cables.", country_isos=("IE",))
    assert provider.supports(asked) and provider.supports_area(asked)
    assert provider.supports(replace(asked, mode=ResearchMode.QUICK))

"""Historical nuclear locations remain bounded, attributed and explicitly non-live."""

import pytest

from ase.adapters.geo.infrastructure import public_infrastructure
from ase.adapters.geo.nuclear import nuclear_facilities
from ase.api.schemas_infrastructure import InfrastructureOut

ROW = {
    "primary_fuel": "Nuclear",
    "gppd_idnr": "GBR0000001",
    "country": "GBR",
    "country_long": "United Kingdom",
    "name": "Example plant",
    "latitude": "52.2",
    "longitude": "1.6",
    "capacity_mw": "1198",
    "year_of_capacity_data": "2019",
    "url": "https://example.org/plant",
    "owner": "Historical operator",
}


def test_packaged_snapshot_has_worldwide_attribution_and_no_live_status():
    data = InfrastructureOut.model_validate(public_infrastructure())
    plants = data.nuclear_facilities
    assert len(plants) == len({p.id for p in plants}) == 195
    assert {"GBR", "USA", "RUS", "CHN", "IRN", "UKR", "ZAF", "ARG"} <= {
        p.country_code for p in plants
    }
    assert "World Resources Institute" in data.nuclear_attribution
    assert "by/4.0" in data.nuclear_licence_url
    assert "7a91cfbb" in data.nuclear_dataset_version
    for plant in plants:
        assert "Historical" in plant.note and "not verified" in plant.note
        assert "status" not in plant.model_dump()
        assert plant.source_url.startswith(("https://", "http://"))


def test_parser_keeps_provenance_and_deduplicates_ids():
    (plant,) = nuclear_facilities([ROW, ROW, {**ROW, "primary_fuel": "Gas"}])
    assert plant["capacity_mw"] == 1198 and plant["capacity_year"] == 2019
    assert plant["source_url"] == ROW["url"]
    assert plant["operator"] == "Historical operator"


@pytest.mark.parametrize(
    "changes",
    [
        {"latitude": "nan"},
        {"longitude": "181"},
        {"latitude": None},
        {"latitude": "bad"},
        {"gppd_idnr": []},
        {"gppd_idnr": "../escape"},
        {"country": "xx"},
        {"name": ""},
    ],
)
def test_malformed_facility_is_skipped(changes):
    assert nuclear_facilities([{**ROW, **changes}]) == []


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "https://u:p@example.org", "https://[bad", "bad url", None]
)
def test_unsafe_links_and_invalid_optional_values_are_not_exposed(url):
    (plant,) = nuclear_facilities(
        [{**ROW, "url": url, "capacity_mw": "nan", "year_of_capacity_data": "unknown"}]
    )
    assert plant["source_url"] == "https://github.com/wri/global-power-plant-database"
    assert plant["capacity_mw"] is None and plant["capacity_year"] is None


def test_snapshot_limit_and_optional_invalid_capacity():
    with pytest.raises(ValueError, match="limit"):
        nuclear_facilities([ROW] * 1001)
    (plant,) = nuclear_facilities([{**ROW, "capacity_mw": "unknown", "owner": None}])
    assert plant["capacity_mw"] is None and plant["operator"] is None

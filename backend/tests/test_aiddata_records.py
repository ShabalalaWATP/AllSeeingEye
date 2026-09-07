"""Native project parsing retains source meaning, precision and immutable identity."""

import hashlib
import json

import pytest

from ase.adapters.research_records.aiddata_records import RELEASE_COMMIT, parse_project
from ase.domain.evidence_geometry import LocationRole


def source(**changes):
    properties = {
        "id": 35756,
        "Recipient.ISO-3": "LAO",
        "Recipient": "Laos",
        "Title": "Synthetic airport project",
        "Status": "Completion",
        "Sector.Name": "TRANSPORT",
        "osm_precision_list": "precise;approximate",
        "Commitment.Year": 2011,
        "Implementation.Start.Year": 2011.0,
        "Completion.Year": 2012,
        "Commitment.Date.(MM/DD/YYYY)": "2011-01-01",
        "Amount.(Constant.USD.2021)": 123.5,
    } | changes
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]],
                    },
                }
            ],
        }
    ).encode()


def test_native_project_preserves_years_derived_geometry_and_monetary_units():
    data = source()
    record = parse_project(data, expected_id="35756")
    assert record.project.commitment_year == 2011
    assert record.project.implementation_year == 2011
    assert record.project.precision == "precise;approximate"
    assert record.amount_constant_usd_2021 == "123.5"
    assert record.geometry.location_role is LocationRole.PROJECT_SITE
    assert "buffered" in record.geometry.method
    assert RELEASE_COMMIT in record.source_url
    assert record.project.source_sha256 == hashlib.sha256(data).hexdigest()


def test_decimal_precision_and_unknown_year_are_not_inferred_from_date_string():
    data = source(**{"Commitment.Year": None}).replace(b"123.5", b"123.12345678901234567890")
    record = parse_project(data, expected_id="35756")
    assert record.project.commitment_year is None
    assert record.amount_constant_usd_2021 == "123.12345678901234567890"


@pytest.mark.parametrize(
    "change",
    [
        {"id": 12},
        {"id": True},
        {"Commitment.Year": 2011.5},
        {"Commitment.Year": True},
        {"Recipient.ISO-3": "lao"},
        {"Title": "x" * 5001},
        {"Amount.(Constant.USD.2021)": float("nan")},
    ],
)
def test_invalid_native_records_fail(change):
    with pytest.raises(ValueError):
        parse_project(source(**change), expected_id="35756")


def test_duplicate_keys_are_rejected():
    with pytest.raises(ValueError):
        parse_project(
            source().replace(b'"id": 35756', b'"id": 35756, "id": 35756'), expected_id="35756"
        )


def test_extreme_decimal_year_is_rejected_before_integer_expansion():
    data = source().replace(b'"Commitment.Year": 2011', b'"Commitment.Year": 1e999999999')
    with pytest.raises(ValueError):
        parse_project(data, expected_id="35756")


@pytest.mark.parametrize("token", [b"1e999999999999999999999999", b"1." + b"1" * 101, b"NaN"])
def test_extreme_number_in_unused_property_has_controlled_failure(token):
    data = source().replace(b'"id": 35756', b'"unused": ' + token + b', "id": 35756')
    with pytest.raises(ValueError):
        parse_project(data, expected_id="35756")


@pytest.mark.parametrize("level", ["collection", "feature"])
def test_explicit_non_wgs84_crs_is_not_reinterpreted(level):
    value = json.loads(source())
    target = value if level == "collection" else value["features"][0]
    target["crs"] = {"type": "name", "properties": {"name": "EPSG:3857"}}
    with pytest.raises(ValueError):
        parse_project(json.dumps(value).encode(), expected_id="35756")

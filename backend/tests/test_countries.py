"""Country resolution: the synthetic index, the packaged Natural Earth data and the stage."""

from __future__ import annotations

from httpx import AsyncClient

from ase.adapters.geo.countries import CountryIndex, load_records
from ase.application.feeds.geo import CountryStage
from ase.domain.events import Point
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]
HOLE = [[4, 4], [6, 4], [6, 6], [4, 6]]
RECORDS = [
    {"iso2": "aa", "iso3": "AAA", "name": "Alpha", "polygons": [[SQUARE, HOLE]]},
    {
        "iso2": "BB",
        "iso3": "BBB",
        "name": "Beta",
        "polygons": [
            [[[20, 0], [30, 0], [30, 10], [20, 10]]],
            [[[170, 0], [180, 0], [180, 5], [170, 5]]],
        ],
    },
    {"iso2": "CC", "iso3": "CCC", "name": "Gamma", "polygons": [[], [[[0, 0], [1, 1]]]]},
]


def test_synthetic_index() -> None:
    index = CountryIndex(RECORDS)
    assert len(index) == 2
    assert index.resolve(2, 2) == "AA"
    assert index.resolve(5, 5) is None  # inside the hole
    assert index.resolve(25, 5) == "BB"
    assert index.resolve(175, 2) == "BB"
    assert index.resolve(50, 50) is None
    alpha = index.get("aa")
    assert alpha is not None and alpha.name == "Alpha" and alpha.iso3 == "AAA"
    assert index.get("CC") is None
    assert [country.name for country in index.countries()] == ["Alpha", "Beta"]
    beta = index.get("BB")
    assert beta is not None
    assert beta.bounds == (20, 0, 180, 10)
    assert beta.centroid == (25, 5)


def test_packaged_natural_earth_data() -> None:
    index = CountryIndex.from_resource()
    assert load_records() is load_records()
    assert len(index) >= 170
    expected = {
        (-0.1276, 51.5072): "GB",  # London
        (30.5234, 50.4501): "UA",  # Kyiv
        (149.13, -35.28): "AU",  # Canberra
        (139.69, 35.69): "JP",  # Tokyo
        (2.3522, 48.8566): "FR",  # Paris (ISO_A2 is -99 in Natural Earth)
        (10.7522, 59.9139): "NO",  # Oslo (same quirk)
        (21.1655, 42.6629): "XK",  # Pristina
        (-175.0, 66.0): "RU",  # Chukotka, east of the antimeridian
        (178.4, -18.1): "FJ",  # Viti Levu
        (-30.0, 30.0): None,  # mid-Atlantic
    }
    for (lon, lat), iso in expected.items():
        assert index.resolve(lon, lat) == iso, (lon, lat)
    britain = index.get("GB")
    assert britain is not None and britain.name == "United Kingdom" and britain.iso3 == "GBR"
    west, south, east, north = britain.bounds
    assert west <= britain.centroid[0] <= east and south <= britain.centroid[1] <= north
    names = [country.name for country in index.countries()]
    assert names == sorted(names)


def test_stage_fills_missing_country_codes() -> None:
    stage = CountryStage(CountryIndex(RECORDS))
    located = make_event("a", point=Point(lon=2.0, lat=2.0))
    tagged = make_event("b", point=Point(lon=2.0, lat=2.0), country_iso="ZZ")
    unlocated = make_event("c", point=None)
    at_sea = make_event("d", point=Point(lon=50.0, lat=50.0))
    result = stage.process([located, tagged, unlocated, at_sea])
    assert [event.country_iso for event in result] == ["AA", "ZZ", None, None]
    assert result[0].id == located.id and result[0].point == located.point


async def test_countries_endpoint(client: AsyncClient, user: User) -> None:
    assert (await client.get("/api/countries")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/countries", headers=bearer(token))
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 170
    britain = next(item for item in items if item["iso2"] == "GB")
    assert britain["name"] == "United Kingdom"
    assert len(britain["bounds"]) == 4 and len(britain["centroid"]) == 2

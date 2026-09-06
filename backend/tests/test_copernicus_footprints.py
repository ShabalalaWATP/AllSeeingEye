"""Synthetic STAC metadata only, with no satellite assets or external requests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ase.adapters.research_records.copernicus import CopernicusFootprintProvider, _polygons
from ase.api.schemas_footprints import FootprintCollectionOut
from ase.domain.footprints import FootprintQuery
from research_feed_helpers import CLOCK, PublicFeed

QUERY = FootprintQuery(
    (-0.2, 51.4, 0.0, 51.6),
    datetime(2026, 9, 1, tzinfo=UTC),
    datetime(2026, 9, 2, tzinfo=UTC),
    True,
)


def data() -> dict:
    return {
        "type": "FeatureCollection",
        "links": [{"rel": "next", "href": "https://untrusted.test/next"}],
        "features": [
            {
                "type": "Feature",
                "id": "S2_SYNTHETIC",
                "collection": "sentinel-2-l2a",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-0.3, 51.3], [0.1, 51.3], [0.1, 51.7], [-0.3, 51.3]]],
                },
                "properties": {
                    "datetime": "2026-09-01T10:00:00Z",
                    "eo:cloud_cover": 20.5,
                    "_private": "not released",
                },
                "assets": {"image": {"href": "https://untrusted.test/image.tif"}},
            }
        ],
    }


async def test_metadata_only_normalised_geojson_and_no_next_or_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=data()))
    result = await CopernicusFootprintProvider(feed.http, CLOCK).search(QUERY)
    await feed.http.aclose()
    assert len(feed.requests) == 1
    assert feed.requests[0].url.host == "stac.dataspace.copernicus.eu"
    assert feed.requests[0].url.params["fields"] == "-assets"
    assert feed.requests[0].url.params["limit"] == "20"
    assert result.status == "completed" and result.truncated
    out = FootprintCollectionOut.from_domain(result)
    feature = out.features[0]
    assert feature.geometry.type == "MultiPolygon"
    assert feature.properties.cloud_cover == 20.5
    assert feature.properties.captured_at == datetime(2026, 9, 1, 10, tzinfo=UTC)
    assert "image.tif" not in out.model_dump_json() and "_private" not in out.model_dump_json()
    assert "not downloaded imagery" in out.limitations


@pytest.mark.parametrize(
    "changes",
    [
        {"disclose_to_provider": False},
        {"bbox": (179, 10, -179, 11)},
        {"bbox": (-20, 0, 20, 1)},
        {"bbox": (0, -100, 1, -99)},
        {"bbox": (float("nan"), 0, 1, 1)},
        {"until": QUERY.since + timedelta(days=15)},
        {"since": QUERY.since.replace(tzinfo=None)},
    ],
)
def test_query_bounds_and_explicit_disclosure(changes: dict) -> None:
    with pytest.raises(ValueError):
        replace(QUERY, **changes)


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_collection",
        "duplicate",
        "too_many",
        "time",
        "cloud",
        "geometry",
        "unclosed",
        "outside",
    ],
)
async def test_invalid_payload_is_unavailable_not_partial(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    payload = data()
    feature = payload["features"][0]
    if mutation == "wrong_collection":
        feature["collection"] = "another"
    if mutation == "duplicate":
        payload["features"] *= 2
    if mutation == "too_many":
        payload["features"] *= 21
    if mutation == "time":
        feature["properties"]["datetime"] = "2020-01-01T00:00:00Z"
    if mutation == "cloud":
        feature["properties"]["eo:cloud_cover"] = 101
    if mutation == "geometry":
        feature["geometry"] = {"type": "Point", "coordinates": [0, 0]}
    if mutation == "unclosed":
        feature["geometry"]["coordinates"][0][-1] = [0, 0]
    if mutation == "outside":
        feature["geometry"]["coordinates"] = [[[10, 10], [11, 10], [11, 11], [10, 10]]]
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=payload))
    result = await CopernicusFootprintProvider(feed.http, CLOCK).search(QUERY)
    await feed.http.aclose()
    assert result.status == "unavailable" and not result.features


def test_global_vertex_budget_and_strict_numeric_coordinates() -> None:
    geometry = data()["features"][0]["geometry"]
    with pytest.raises(ValueError, match="vertex"):
        _polygons(geometry, 3)
    geometry["coordinates"][0][0][0] = True
    with pytest.raises(ValueError, match="coordinate"):
        _polygons(geometry, 10)


async def test_empty_and_transport_failure_are_distinct(monkeypatch: pytest.MonkeyPatch) -> None:
    for response, status in [
        (httpx.Response(200, json={"type": "FeatureCollection", "features": []}), "empty"),
        (httpx.Response(403), "unavailable"),
    ]:
        feed = PublicFeed(monkeypatch, response)
        result = await CopernicusFootprintProvider(feed.http, CLOCK).search(QUERY)
        await feed.http.aclose()
        assert result.status == status

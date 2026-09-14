"""Public CARS 511 catalogues: parsing, stream host policy and fixed requests."""

import json
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.geo.camera_americas import build_sources
from ase.adapters.geo.camera_americas_cars import (
    CONFIGS,
    CarsCameraSource,
    catalogue_url,
    parse_catalogue,
    parse_feature,
)

CFG = {cfg.id: cfg for cfg in CONFIGS}


def feature(**changes: object) -> dict[str, object]:
    return {
        "title": "MN 252: T.H.252 NB @ Brookdale Dr",
        "uri": "camera/503810",
        "features": [{"geometry": {"type": "Point", "coordinates": [-93.29007, 45.09448]}}],
        "__typename": "Camera",
        "active": True,
        "views": [
            {
                "category": "VIDEO",
                "url": "https://public.carsprogram.org/cameras/MN/C2524",
                "sources": [
                    {
                        "type": "application/x-mpegURL",
                        "src": "https://video.dot.state.mn.us/public/C2524.stream/playlist.m3u8",
                    }
                ],
            }
        ],
        **changes,
    }


def payload(rows: list[object]) -> bytes:
    return json.dumps({"data": {"mapFeaturesQuery": {"mapFeatures": rows}}}).encode()


def test_feature_keeps_snapshot_open_stream_and_operator_link() -> None:
    cam = parse_feature(CFG["minnesota"], feature())
    assert cam is not None
    assert cam.id == "minnesota:503810"
    assert cam.snapshot_url == "https://public.carsprogram.org/cameras/MN/C2524"
    assert cam.stream_url == "https://video.dot.state.mn.us/public/C2524.stream/playlist.m3u8"
    assert cam.stream_type == "hls"
    assert cam.external_url == "https://511mn.org/?show=camera%2F503810"


@pytest.mark.parametrize(
    "src",
    [
        "https://video.dot.state.mn.us/public/C2524.stream/playlist.m3u8?token=signed",
        "https://video.evil.test/public/C2524.stream/playlist.m3u8",
    ],
)
def test_signed_or_unlisted_streams_are_not_offered(src: str) -> None:
    views = [
        {
            "url": "https://public.carsprogram.org/cameras/MN/C1",
            "sources": [{"type": "application/x-mpegURL", "src": src}],
        }
    ]
    cam = parse_feature(CFG["minnesota"], feature(views=views))
    assert cam is not None and cam.stream_url is None and cam.snapshot_url


def test_states_without_stream_hosts_offer_snapshots_only() -> None:
    row = feature(
        features=[{"geometry": {"coordinates": [-71.0847, 42.39281]}}],
        views=[
            {
                "url": "https://public.carsprogram.org/cameras/MA/435503-fullJpeg.jpg",
                "sources": [
                    {
                        "type": "application/x-mpegURL",
                        "src": "https://restream-5.trafficland.com/live/1.m3u8",
                    }
                ],
            }
        ],
    )
    cam = parse_feature(CFG["massachusetts"], row)
    assert cam is not None and cam.stream_url is None
    # Iowa's own image host is not Massachusetts's, and positions stay inside each state.
    assert parse_feature(CFG["iowa"], row) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"__typename": "Event"},
        {"active": False},
        {"uri": "camera/../1"},
        {"features": [{"geometry": {"coordinates": [10, 10]}}]},
        {"features": []},
    ],
)
def test_rejected_features(changes: dict[str, object]) -> None:
    assert parse_feature(CFG["minnesota"], feature(**changes)) is None


def test_unapproved_image_leaves_only_the_operator_link() -> None:
    cam = parse_feature(CFG["minnesota"], feature(views=[{"url": "https://evil.test/a.jpg"}]))
    assert cam is not None and cam.snapshot_url is None and cam.stream_url is None
    assert cam.external_url == "https://511mn.org/?show=camera%2F503810"


def test_catalogue_shape_and_query() -> None:
    assert (
        len(parse_catalogue(CFG["minnesota"], json.loads(payload([feature(), "x", feature()]))))
        == 1
    )
    for bad in ({}, {"data": None}, {"data": {"mapFeaturesQuery": {"mapFeatures": {}}}}):
        with pytest.raises(ValueError, match="CARS"):
            parse_catalogue(CFG["minnesota"], bad)
    url = catalogue_url(CFG["kansas"])
    assert url.startswith("https://www.kandrive.gov/api/graphql?")
    variables = json.loads(parse_qs(urlsplit(url).query)["variables"][0])["input"]
    assert (variables["south"], variables["north"], variables["west"], variables["east"]) == (
        36.9,
        40.1,
        -102.1,
        -94.5,
    )


async def test_source_fetches_the_fixed_url_and_rejects_empty_catalogues() -> None:
    http = AsyncMock()
    http.get_bytes.return_value = payload([feature()])
    source = CarsCameraSource(CFG["minnesota"], http)
    assert len(await source.fetch()) == 1
    http.get_bytes.assert_awaited_once_with(
        catalogue_url(CFG["minnesota"]), conditional=False, max_redirects=0
    )
    http.get_bytes.return_value = payload([])
    with pytest.raises(ValueError, match="no usable"):
        await source.fetch()
    ids = {source.id for source in build_sources(AsyncMock())}
    assert {"minnesota", "iowa", "kansas", "massachusetts"} <= ids

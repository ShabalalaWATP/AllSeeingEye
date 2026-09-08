"""Paging completeness and upstream failure regression checks."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.geo.camera_americas import AmericanCameraSource
from ase.adapters.geo.camera_americas_ibi import CONFIGS, IbiCameraSource
from ase.adapters.geo.camera_americas_parsers import parse_row


async def test_caltrans_reads_all_pages_and_rejects_missing_page():
    http = AsyncMock()
    record = {
        "attributes": {
            "OBJECTID": 1,
            "locationName": "SR-20",
            "latitude": 39,
            "longitude": -123,
            "currentImageURL": "https://cwwp2.dot.ca.gov/a.jpg",
        }
    }
    record2 = {"attributes": {**record["attributes"], "OBJECTID": 2}}
    http.get_bytes.side_effect = [
        json.dumps({"features": [record], "exceededTransferLimit": True}).encode(),
        json.dumps({"features": [record2]}).encode(),
    ]
    result = await AmericanCameraSource("caltrans", http).fetch()
    assert len(result) == 2 and "resultOffset=1" in http.get_bytes.call_args.args[0]
    http.get_bytes.side_effect = [
        b'{"features":[{}],"exceededTransferLimit":true}',
        b'{"features":[]}',
    ]
    with pytest.raises(ValueError, match="Incomplete"):
        await AmericanCameraSource("caltrans", http).fetch()


def test_oregon_spaces_are_encoded_and_paths_rejected():
    row = {
        "attributes": {
            "cameraId": 1,
            "title": "Road",
            "latitude": 45,
            "longitude": -123,
            "filename": "I-5 SB @ Main (South).JPG",
        }
    }
    cam = parse_row("oregon", "ODOT", "https://tripcheck.com", row)
    assert cam and "%20" in cam.snapshot_url and "%40" in cam.snapshot_url
    row["attributes"]["filename"] = "../private.jpg"
    assert parse_row("oregon", "ODOT", "https://tripcheck.com", row) is None


async def test_transient_server_failure_retries_but_denial_does_not():

    http = AsyncMock()
    http.get_bytes.side_effect = [
        FeedFetchError("HTTP 500 from provider"),
        b'{"recordsTotal":0,"data":[]}',
    ]
    assert await IbiCameraSource(CONFIGS[1], http).fetch() == ()
    assert http.get_bytes.await_count == 2
    http.reset_mock()
    http.get_bytes.side_effect = FeedFetchError("HTTP 403 from provider")
    with pytest.raises(FeedFetchError):
        await IbiCameraSource(CONFIGS[1], http).fetch()
    assert http.get_bytes.await_count == 1

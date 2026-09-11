"""Official WSDOT camera access uses a protected, server-side query credential."""

import asyncio
import json
import logging
import traceback
from datetime import timedelta
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.secret_urls import HTTP_LOGGERS, SecretFeedUrl
from ase.adapters.geo.camera_americas import build_sources
from ase.adapters.geo.camera_americas_parsers import parse_row
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_wsdot import ENDPOINT, ORIGIN, SOURCE_URL, WsdotCameraSource

KEY = "synthetic-wsdot-code"
ROW = {
    "CameraID": 42,
    "Title": "I-5 at Main Street",
    "CameraLocation": {"Latitude": 47.6, "Longitude": -122.3},
    "ImageURL": "https://images.wsdot.wa.gov/camera.jpg",
    "IsActive": True,
}


def test_wsdot_excludes_provider_marked_inactive_cameras():
    row = {**ROW, "IsActive": False}
    assert parse_row("wsdot", "WSDOT", "https://www.wsdot.wa.gov/traffic/api/", row) is None


async def test_configured_wsdot_replaces_retired_endpoint_without_duplicate_provider():
    http = AsyncMock()
    http.get_secret_bytes.return_value = json.dumps([ROW, ROW]).encode()
    sources = build_sources(http, wsdot_access_code=KEY)
    assert len(sources) == len({source.id for source in sources}) == 21
    source = next(source for source in sources if source.id == "wsdot")
    cameras = await source.fetch()
    assert len(cameras) == 1 and cameras[0].id == "wsdot:42"
    assert cameras[0].stream_url is None and cameras[0].captured_at is None
    assert KEY not in repr(cameras) + repr(source)
    target = http.get_secret_bytes.await_args.args[0]
    assert isinstance(target, SecretFeedUrl)
    assert target.origin == ORIGIN
    assert target.url.split("?")[0] == ENDPOINT
    assert parse_qs(urlsplit(target.url).query) == {"AccessCode": [KEY]}
    assert cameras[0].source_url == SOURCE_URL
    assert KEY not in repr(target)
    http.get_bytes.assert_not_awaited()


@pytest.mark.parametrize("key", [None, ""])
async def test_unconfigured_provider_is_registered_but_makes_no_request(key):
    http = AsyncMock()
    source = next(s for s in build_sources(http, wsdot_access_code=key) if s.id == "wsdot")
    with pytest.raises(ValueError, match="ASE_WSDOT_ACCESS_CODE"):
        await source.fetch()
    http.get_bytes.assert_not_awaited()
    http.get_secret_bytes.assert_not_awaited()


@pytest.mark.parametrize("key", ["bad\nkey", "bad key", "bad\x00key", "ü", "x" * 513])
def test_invalid_access_code_is_rejected_without_echoing_it(key):
    http = AsyncMock()
    with pytest.raises(ValueError, match="WSDOT access code configuration") as error:
        WsdotCameraSource(http, key)
    assert key not in str(error.value)
    http.get_secret_bytes.assert_not_awaited()


async def test_reserved_characters_cannot_inject_additional_query_parameters():
    http = AsyncMock()
    http.get_secret_bytes.return_value = json.dumps([ROW]).encode()
    key = "synthetic?&AccessCode=other#/%code"
    await WsdotCameraSource(http, key).fetch()
    target = http.get_secret_bytes.await_args.args[0]
    assert parse_qs(urlsplit(target.url).query) == {"AccessCode": [key]}
    assert not urlsplit(target.url).fragment


@pytest.mark.parametrize("status", [200, 302, 304, 401, 403, 429, 500])
async def test_query_credential_never_enters_logs_errors_cache_or_redirects(
    monkeypatch, caplog, status
):
    caplog.set_level(logging.DEBUG)
    guarded, requests = [], []

    async def public_host(url):
        guarded.append(url)

    monkeypatch.setattr(feed_http, "assert_public_host", public_host)

    def respond(request):
        requests.append(request)
        for name in HTTP_LOGGERS:
            logging.getLogger(name).debug("request %s", request.url)
        return httpx.Response(
            status,
            content=json.dumps([ROW]).encode() if status == 200 else KEY.encode(),
            headers={"location": "https://other.example/steal", "etag": "public-etag"},
        )

    http = FeedHttpClient("tests", client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        source = WsdotCameraSource(http, KEY)
        if status == 200:
            assert len(await source.fetch()) == 1
        else:
            with pytest.raises(ValueError, match="catalogue unavailable") as error:
                await source.fetch()
            assert KEY not in "".join(traceback.format_exception(error.value))
        assert len(requests) == len(guarded) == 1
        assert requests[0].url.host == urlsplit(ORIGIN).hostname
        assert requests[0].url.params["AccessCode"] == KEY
        assert "authorization" not in requests[0].headers
        assert http._validators == {}
        assert KEY not in repr(source) + caplog.text
    finally:
        await http.aclose()


@pytest.mark.parametrize(
    "payload",
    [
        b"[]",
        json.dumps({"error": KEY}).encode(),
        f"invalid JSON {KEY}".encode(),
        b"[" * 20_000 + b"0" + b"]" * 20_000,
        json.dumps([{**ROW, "ImageURL": "https://evil.example/camera.jpg"}]).encode(),
    ],
    ids=["empty", "provider-error", "invalid-json", "deep-json", "untrusted-media"],
)
async def test_unusable_payload_fails_safely(payload):
    http = AsyncMock()
    http.get_secret_bytes.return_value = payload
    with pytest.raises(ValueError, match="catalogue unavailable") as error:
        await WsdotCameraSource(http, KEY).fetch()
    assert KEY not in "".join(traceback.format_exception(error.value))
    assert http.get_secret_bytes.await_count == 1


async def test_record_limit_and_inactive_flag_preserve_catalogue_bounds():
    http = AsyncMock()
    rows = [{**ROW, "CameraID": key} for key in range(5001)]
    rows[0]["IsActive"] = False
    http.get_secret_bytes.return_value = json.dumps(rows).encode()
    result = await WsdotCameraSource(http, KEY).fetch()
    assert len(result) == 4999
    assert "wsdot:0" not in {camera.id for camera in result}
    assert "wsdot:5000" not in {camera.id for camera in result}


async def test_cancellation_is_not_converted_to_provider_failure():
    http = AsyncMock()
    http.get_secret_bytes.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await WsdotCameraSource(http, KEY).fetch()


@pytest.fixture
def settings(settings):
    settings.wsdot_access_code = SecretStr(KEY)
    return settings


async def test_production_wiring_retains_shared_cache_and_isolates_failed_refresh(
    container, user, clock, monkeypatch
):
    fetch = AsyncMock(return_value=json.dumps([ROW]).encode())
    monkeypatch.setattr(CameraHttpClient, "get_secret_bytes", fetch)
    assert container.cameras.provider_ids.count("wsdot") == 1
    first, second = await asyncio.gather(
        container.cameras.catalogue(user, "wsdot"), container.cameras.catalogue(user, "wsdot")
    )
    assert first == second and len(first.cameras) == 1
    assert fetch.await_count == 1
    assert parse_qs(urlsplit(fetch.await_args.args[0].url).query) == {"AccessCode": [KEY]}
    assert KEY not in repr(container.settings) + repr(first)
    assert container.store.stats().total == 0
    clock.advance(timedelta(minutes=16))
    fetch.side_effect = FeedFetchError(f"request failed {KEY}")
    stale = await container.cameras.catalogue(user, "wsdot")
    assert len(stale.cameras) == 1 and fetch.await_count == 2
    status = next(provider for provider in stale.providers if provider.id == "wsdot")
    assert status.status == "stale" and KEY not in repr(stale)
    await container.cameras.catalogue(user, "wsdot")
    assert fetch.await_count == 2

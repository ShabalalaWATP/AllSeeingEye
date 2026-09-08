"""CelesTrak error classification uses a bounded prefix, never arbitrary provider text."""

import httpx
import pytest

from ase.adapters.feeds.http import FeedHttpStatusError
from ase.adapters.feeds.satellite_http import ElementsNotUpdated, SatelliteHttpClient
from ase.adapters.feeds.satellites import ACTIVE_SATELLITES

UNCHANGED = b"GP data has not updated since your last successful download of GROUP=active"


@pytest.mark.parametrize(
    ("status", "url", "body", "expected"),
    [
        (403, ACTIVE_SATELLITES.url, UNCHANGED, ElementsNotUpdated),
        (403, ACTIVE_SATELLITES.url, b"Access blocked 192.0.2.1", FeedHttpStatusError),
        (404, ACTIVE_SATELLITES.url, UNCHANGED, FeedHttpStatusError),
        (403, "https://example.com/", UNCHANGED, FeedHttpStatusError),
        (403, ACTIVE_SATELLITES.url, b"x" * 4096 + UNCHANGED, FeedHttpStatusError),
    ],
)
async def test_only_documented_response_is_unchanged(status, url, body, expected, monkeypatch):
    async def no_dns(url):
        return None

    monkeypatch.setattr("ase.adapters.feeds.http.assert_public_host", no_dns)
    client = SatelliteHttpClient(
        "test-agent",
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(status, content=body))
        ),
    )
    try:
        with pytest.raises(expected) as result:
            await client.get_text(url)
        assert "192.0.2.1" not in str(result.value)
    finally:
        await client.aclose()

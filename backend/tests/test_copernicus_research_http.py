"""Catalogue composition against guarded HTTP with mocked responses."""

from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research_records.copernicus import CopernicusFootprintProvider
from ase.adapters.research_records.copernicus_research import CopernicusResearchProvider
from ase.domain.research import CollectionStatus
from test_copernicus_research import NOW, QUERY
from test_copernicus_research_geometry import payload


@pytest.mark.parametrize("response_status", [200, 503, 302])
async def test_bounded_fixed_origin_request_and_no_private_terms(monkeypatch, response_status):
    requests, guarded = [], []

    async def guard(url):
        guarded.append(url)

    def respond(request):
        requests.append(request)
        return httpx.Response(
            response_status,
            json=payload(),
            headers={
                "Location": "https://untrusted.test/redirect",
            },
        )

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    client = FeedHttpClient(
        "ASE test", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        provider = CopernicusResearchProvider(
            CopernicusFootprintProvider(
                client,
                SimpleNamespace(now=lambda: NOW),
            )
        )
        query = replace(
            QUERY, question="Private question", terms=("Private name",), languages=("zh-hans",)
        )
        result = await provider.collect(query)
    finally:
        await client.aclose()
    assert len(requests) == 1 and len(guarded) == 1
    url = requests[0].url
    assert url.host == "stac.dataspace.copernicus.eu" and url.path == "/v1/search"
    assert dict(url.params) == {
        "collections": "sentinel-2-l2a",
        "bbox": "0.0,0.0,1.0,1.0",
        "datetime": "2026-09-06T00:00:00Z/2026-09-07T00:00:00Z",
        "limit": "20",
        "fields": "-assets",
        "sortby": "-properties.datetime",
    }
    assert "Private" not in str(url) and "zh-hans" not in str(url)
    if response_status == 200:
        assert result.attempts[0].status == CollectionStatus.COMPLETED
        assert result.items[0].published_at is None
    else:
        assert result.attempts[0].status == CollectionStatus.UNAVAILABLE
        assert not result.items

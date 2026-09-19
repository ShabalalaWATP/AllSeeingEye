"""The official KEV mirror restores collection when CISA's CDN refuses a request."""

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.cisa_kev import SPEC, CisaKevConnector
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from feeds_helpers import NOW, FakeClock, load_fixture

MIRROR = (
    "https://raw.githubusercontent.com/cisagov/kev-data/"
    "develop/known_exploited_vulnerabilities.json"
)


@pytest.mark.parametrize(
    "primary,mirror,outcome",
    [
        (200, 200, "events"),
        (403, 200, "events"),
        (403, 304, "empty"),
        (304, 200, "empty"),
        (429, 200, "error"),
        (500, 200, "error"),
        (403, 503, "error"),
        (403, 200, "invalid"),
    ],
)
async def test_kev_uses_only_official_mirror_on_access_refusal(
    monkeypatch: pytest.MonkeyPatch, primary: int, mirror: int, outcome: str
) -> None:
    guarded: list[str] = []
    requested: list[str] = []

    async def guard(url: str) -> None:
        guarded.append(url)

    def respond(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        assert url in {SPEC.url, MIRROR}
        status = primary if url == SPEC.url else mirror
        data = {} if outcome == "invalid" else load_fixture("cisa_kev.json")
        return httpx.Response(status, json=data)

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    http = FeedHttpClient(
        "ASE test", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        connector = CisaKevConnector(http, FakeClock(NOW))
        if outcome in {"error", "invalid"}:
            with pytest.raises(FeedFetchError):
                await connector.fetch()
        else:
            events = await connector.fetch()
            assert bool(events) is (outcome == "events")
            assert all(event.source_id == "cisa_kev" for event in events)
    finally:
        await http.aclose()
    assert requested == guarded == ([SPEC.url, MIRROR] if primary == 403 else [SPEC.url])

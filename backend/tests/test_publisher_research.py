"""Private publisher reuse preserves provenance, content limits and guarded request bounds."""

from dataclasses import replace

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.publisher import PUBLISHER_SEEDS, PublisherFeedResearchProvider
from ase.application.research.collection import ResearchCollector
from ase.domain.research import CollectionStatus
from ase.domain.research_area import direct_area_from_geometry
from ase.domain.source_controls import source_control_keys
from research_feed_helpers import CLOCK, QUERY, PublicFeed, item, rss

SEEDS = {seed.spec.id: seed for seed in PUBLISHER_SEEDS}


async def test_scmp_uses_canonical_https_feed_without_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []
    guarded: list[str] = []

    async def guard(url: str) -> None:
        guarded.append(url)

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        # The unsuffixed URL redirects through HTTP. Private collection must use
        # the verified HTTPS feed directly, without increasing its request budget.
        if request.url.path == "/rss/91/feed":
            return httpx.Response(301, headers={"location": "http://www.scmp.com/rss/91/feed/"})
        assert request.url == "https://www.scmp.com/rss/91/feed/"
        return httpx.Response(200, text=rss(item()))

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    http = FeedHttpClient(
        "ASE test", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        batch = await PublisherFeedResearchProvider(http, CLOCK, SEEDS["scmp_news"]).collect(QUERY)
    finally:
        await http.aclose()
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert len(batch.items) == len(requests) == len(guarded) == 1
    assert batch.items[0].attributes["original_source_id"] == "scmp_news"


@pytest.mark.parametrize("seed_id", SEEDS)
async def test_one_native_feed_request_preserves_identity_and_discards_article_text(
    monkeypatch: pytest.MonkeyPatch, seed_id: str
) -> None:
    seed = SEEDS[seed_id]
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = PublisherFeedResearchProvider(feed.http, CLOCK, seed)
    # Private collection only queries a publisher in a requested research language.
    language = seed.spec.language
    query = QUERY if language == "en" else replace(QUERY, languages=(language,))
    batch = await provider.collect(query)
    assert len(feed.requests) == len(feed.guarded) == 1
    request = feed.requests[0]
    assert str(request.url) == seed.spec.url
    assert QUERY.question not in str(request.url) and QUERY.terms[0] not in str(request.url)
    assert "if-none-match" not in request.headers and "if-modified-since" not in request.headers
    event = batch.items[0]
    assert batch.attempts[0].source_id == event.source_id == provider.id
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert batch.attempts[0].language == language and event.language == language
    assert event.grade == "F6" and event.summary is None
    assert event.attributes["original_source_id"] == seed_id
    assert event.attributes["original_source_organisation"] == seed.spec.organisation
    assert event.attributes["collection_source_id"] == provider.id
    # A live and private fetch of one item are one event, not extra corroboration.
    live = (await RssConnector(feed.http, CLOCK, seed.spec, seed.options).fetch())[0]
    assert (event.id, event.url, event.published_at, event.source_dates) == (
        live.id,
        live.url,
        live.published_at,
        live.source_dates,
    )
    assert event.tags == live.tags
    await feed.http.aclose()


async def test_headline_matching_is_local_and_dates_use_half_open_publication_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = rss(
        item("start", title="RAIL DISRUPTION reported", date="2026-09-05T00:00:00Z")
        + item("last", date="2026-09-05T23:59:59Z")
        + item("before", date="2026-09-04T23:59:59Z")
        + item("end", date="2026-09-06T00:00:00Z")
        + item("unknown", date="")
        + item("invalid", date="not-a-date")
        + item("body-only", title="A different headline").replace(
            "A report from the crossing.", "Rail disruption reported in full article text."
        )
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    batch = await PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"]).collect(QUERY)
    await feed.http.aclose()
    assert [event.url for event in batch.items] == [
        "https://publisher.example/start",
        "https://publisher.example/last",
    ]
    assert all(event.summary is None for event in batch.items)


@pytest.mark.parametrize(
    "language,terms", [("fr", QUERY.terms), ("en", ()), ("en", ("x" * 300,) * 4)]
)
async def test_unsupported_language_or_missing_bounded_phrases_make_no_request(
    monkeypatch: pytest.MonkeyPatch, language: str, terms: tuple[str, ...]
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"])
    batch = await provider.collect(replace(QUERY, languages=(language,), terms=terms))
    await feed.http.aclose()
    assert batch.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not feed.requests and not feed.guarded


async def test_country_choice_does_not_create_geometry_and_area_collection_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"])
    country = await provider.collect(replace(QUERY, country_iso="CN"))
    assert country.items[0].point is None and country.items[0].country_iso is None
    assert "does not establish incident geography" in country.attempts[0].explanation
    area = direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]],
                    },
                }
            ],
        }
    )
    query = replace(QUERY, area=area)
    assert not provider.supports(query)
    direct = await provider.collect(query)
    planned = await ResearchCollector([provider]).collect(query)
    await feed.http.aclose()
    assert direct.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert planned.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert len(feed.requests) == len(feed.guarded) == 1


async def test_feed_truncation_is_visible_and_duplicate_items_keep_one_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = rss("".join(item(str(index // 2)) for index in range(230)))
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    batch = await PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"]).collect(QUERY)
    await feed.http.aclose()
    assert len(batch.items) == batch.attempts[0].result_count == 100
    assert batch.items[-1].url == "https://publisher.example/99"
    assert all(event.attributes["feed_items_truncated"] is True for event in batch.items)
    assert batch.items[0].attributes["feed_items_available"] == 230


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "http://127.0.0.1/private", "https://u:p@publisher.example"]
)
async def test_untrusted_article_links_are_not_retained_or_fetched(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    payload = rss(item(extra=f'<source url="{url}">Claimed upstream</source>')).replace(
        "https://publisher.example/1", url
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    batch = await PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"]).collect(QUERY)
    await feed.http.aclose()
    assert batch.items[0].url is None
    assert batch.items[0].attributes["original_publisher_url"] is None
    assert len(feed.requests) == len(feed.guarded) == 1


@pytest.mark.parametrize(
    "error,status",
    [(TimeoutError, CollectionStatus.TIMED_OUT), (FeedFetchError, CollectionStatus.FAILED)],
)
async def test_host_guard_and_deadline_failures_are_safe_receipts(
    monkeypatch: pytest.MonkeyPatch, error: type[Exception], status: CollectionStatus
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))

    async def blocked(url: str) -> None:
        raise error(f"Sensitive upstream request: {url}")

    monkeypatch.setattr(feed_http, "assert_public_host", blocked)
    batch = await PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"]).collect(QUERY)
    await feed.http.aclose()
    assert batch.attempts[0].status is status
    assert not batch.items and not feed.requests
    assert batch.attempts[0].source_id == "research_publisher_bbc_world"
    assert "Sensitive" not in repr(batch)


@pytest.mark.parametrize(
    "status,body", [(200, "<html>Private response</html>"), (403, "Private response"), (302, "")]
)
async def test_failure_is_not_empty_coverage_and_redirects_are_not_followed(
    monkeypatch: pytest.MonkeyPatch, status: int, body: str
) -> None:
    feed = PublicFeed(
        monkeypatch,
        httpx.Response(status, text=body, headers={"location": "https://other.example/Private"}),
    )
    batch = await PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"]).collect(QUERY)
    await feed.http.aclose()
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert not batch.items and len(feed.requests) == len(feed.guarded) == 1
    assert "Private" not in repr(batch)


async def test_empty_headline_match_has_a_truthful_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(title="Unrelated report"))))
    batch = await PublisherFeedResearchProvider(feed.http, CLOCK, SEEDS["bbc_world"]).collect(QUERY)
    await feed.http.aclose()
    assert batch.attempts[0].status is CollectionStatus.EMPTY
    assert (
        batch.attempts[0].result_count == 0
        and "not a complete archive" in batch.attempts[0].explanation
    )


def test_reviewed_seeds_are_distinct_and_inherit_original_admission() -> None:
    # Publisher research sources follow the reviewed feed catalogue as it grows.
    assert len(PUBLISHER_SEEDS) == len(SEEDS) == 72
    assert not SEEDS.keys() & {seed.spec.id for seed in REGIONAL_SEEDS}
    for source_id in SEEDS:
        derived = f"research_publisher_{source_id}"
        assert source_control_keys(derived) == (derived, source_id)


@pytest.mark.parametrize(
    "seed",
    [
        REGIONAL_SEEDS[0],
        replace(
            PUBLISHER_SEEDS[0],
            spec=replace(PUBLISHER_SEEDS[0].spec, url="https://other.example/rss"),
        ),
    ],
)
def test_other_feeds_and_modified_urls_cannot_be_registered(seed) -> None:
    with pytest.raises(ValueError, match="approved official or outlet"):
        PublisherFeedResearchProvider(None, CLOCK, seed)  # type: ignore[arg-type]

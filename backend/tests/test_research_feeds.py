"""On-demand news/social collection stays bounded, private and provenance-aware."""

from dataclasses import replace

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.rss_seeds_social import SOCIAL_SEEDS
from ase.adapters.research.news import GoogleNewsResearchProvider
from ase.adapters.research.social import SocialFeedResearchProvider
from ase.domain.events import Category, Reliability
from ase.domain.research import CollectionStatus
from research_feed_helpers import CLOCK, QUERY, PublicFeed, item, rss


async def test_news_one_guarded_request_has_explicit_terms_language_and_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    query = replace(QUERY, languages=("fr", "en"), terms=("rail disruption", "sabotage"))
    provider = GoogleNewsResearchProvider(feed.http, CLOCK, "fr")
    async with feed.http._client:
        result = await provider.collect(query)
    assert len(feed.requests) == len(feed.guarded) == 1
    request = feed.requests[0]
    assert request.url.host == "news.google.com" and request.url.path == "/rss/search"
    assert request.url.params["q"] == (
        '("rail disruption" OR "sabotage") after:2026-09-04 before:2026-09-07'
    )
    assert request.url.params["hl"] == "fr" and request.url.params["ceid"] == "FR:fr"
    assert query.question not in str(request.url)
    assert result.attempts[0].status is CollectionStatus.COMPLETED
    assert result.attempts[0].language == "fr"
    assert "not guaranteed" in result.attempts[0].explanation


async def test_news_does_not_inherit_aggregator_reliability_or_guess_unknown_publishers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = rss(
        item(extra='<source url="https://outlet.example">Declared Outlet</source>')
        + item("2", "Another article without publisher")
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    declared, unknown = result.items
    assert declared.attributes["original_publisher"] == "Declared Outlet"
    assert declared.attributes["original_publisher_url"] == "https://outlet.example"
    assert unknown.attributes["original_publisher"] is None
    assert all(event.grade == "F6" for event in result.items)
    assert all(event.attributes["provenance_status"] == "unverified" for event in result.items)
    assert all(event.source_id == "research_google_news_en" for event in result.items)


async def test_exact_dates_exclude_unknown_dates_and_apply_half_open_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = (
        "2026-09-04T23:59:59Z",
        "2026-09-05T00:00:00Z",
        "2026-09-05T23:59:59Z",
        "2026-09-06T00:00:00Z",
        "",
        "invalid-date",
    )
    feed = PublicFeed(
        monkeypatch,
        httpx.Response(
            200, text=rss("".join(item(str(i), date=date) for i, date in enumerate(dates)))
        ),
    )
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    assert [event.url for event in result.items] == [
        "https://publisher.example/1",
        "https://publisher.example/2",
    ]


@pytest.mark.parametrize(
    "language,terms",
    [("xx", QUERY.terms), ("fr", QUERY.terms), ("en", ()), ("en", ("x" * 300,) * 4)],
)
async def test_unsupported_editions_or_unbounded_terms_do_not_make_requests(
    monkeypatch: pytest.MonkeyPatch,
    language: str,
    terms: tuple[str, ...],
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = GoogleNewsResearchProvider(feed.http, CLOCK, language)
    query = replace(QUERY, terms=terms)
    assert not provider.supports(query)
    result = await provider.collect(query)
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not feed.requests and not feed.guarded


async def test_redirect_is_not_followed_or_disclosed(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "private-question-term"
    feed = PublicFeed(
        monkeypatch, httpx.Response(302, headers={"location": f"https://other.example/{secret}"})
    )
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(
        replace(QUERY, terms=(secret,))
    )
    await feed.http.aclose()
    assert len(feed.requests) == len(feed.guarded) == 1
    assert result.attempts[0].status is CollectionStatus.FAILED
    assert secret not in repr(result) and "other.example" not in repr(result)


@pytest.mark.parametrize(
    "body",
    [
        "<rss>",
        "<html>Not a feed</html>",
        '<!DOCTYPE rss [<!ENTITY private SYSTEM "file:///private">]><rss>&private;</rss>',
    ],
)
async def test_invalid_and_entity_xml_returns_safe_failed_receipt(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=body))
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    assert not result.items and result.attempts[0].status is CollectionStatus.FAILED
    assert body not in repr(result)


async def test_feed_cap_and_duplicate_ids_bound_results(monkeypatch: pytest.MonkeyPatch) -> None:
    feed = PublicFeed(
        monkeypatch, httpx.Response(200, text=rss("".join(item(str(i // 2)) for i in range(220))))
    )
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    assert len(result.items) == result.attempts[0].result_count == 100


async def test_unsafe_links_and_oversized_feed_text_are_not_retained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = rss(
        item(
            title="Rail disruption " + "x" * 500,
            extra='<source url="https://u:p@outlet.example">Outlet</source>',
        )
        .replace("https://publisher.example/1", "javascript:alert(1)")
        .replace("A report from the crossing.", "x" * 3000)
        + item("2", title="")
        + item("3", extra='<source url="https://[invalid">Outlet</source>')
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    assert len(result.items) == 2
    assert result.items[0].url is None
    assert len(result.items[0].title) == 300 and len(result.items[0].summary or "") == 2000
    assert all(event.attributes["original_publisher_url"] is None for event in result.items)


async def test_collection_timeout_has_safe_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))

    async def timeout(url: str) -> None:
        raise TimeoutError(f"Sensitive URL {url}")

    monkeypatch.setattr(feed_http, "assert_public_host", timeout)
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.TIMED_OUT
    assert "Sensitive" not in repr(result) and not feed.requests


async def test_social_atom_matches_terms_and_preserves_account_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = """<feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <id>post-1</id><title>RAIL DISRUPTION reported</title>
      <published>2026-09-05T12:00:00Z</published>
      <author><name>Named account</name><uri>https://social.example/@account</uri></author>
      <link href="https://social.example/post/1"/><summary>Public claim</summary>
    </entry><entry><id>post-2</id><title>Unrelated post</title>
      <published>2026-09-05T12:00:00Z</published></entry></feed>"""
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=body))
    seed = SOCIAL_SEEDS[0]
    provider = SocialFeedResearchProvider(feed.http, CLOCK, seed)
    result = await provider.collect(QUERY)
    await feed.http.aclose()
    assert len(feed.requests) == len(result.items) == 1
    assert str(feed.requests[0].url) == seed.spec.url
    assert result.items[0].attributes["original_account"] == "Named account"
    assert result.items[0].attributes["original_account_url"] == "https://social.example/@account"
    assert result.items[0].reliability is Reliability.F
    assert "not a platform-wide search" in result.attempts[0].explanation


async def test_social_language_selection_and_empty_recent_feed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(title="Unrelated"))))
    seed = SOCIAL_SEEDS[0]
    provider = SocialFeedResearchProvider(feed.http, CLOCK, seed)
    unsupported = await provider.collect(replace(QUERY, languages=("fr",)))
    assert unsupported.attempts[0].status is CollectionStatus.UNSUPPORTED and not feed.requests
    empty = await provider.collect(QUERY)
    await feed.http.aclose()
    assert empty.attempts[0].status is CollectionStatus.EMPTY
    assert empty.attempts[0].result_count == 0


async def test_blocked_guard_never_reaches_transport_and_errors_are_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))

    async def blocked(url: str) -> None:
        raise FeedFetchError(f"Blocked secret query URL {url}")

    monkeypatch.setattr(feed_http, "assert_public_host", blocked)
    result = await GoogleNewsResearchProvider(feed.http, CLOCK).collect(QUERY)
    await feed.http.aclose()
    assert not feed.requests and not result.items
    assert "secret" not in repr(result) and QUERY.terms[0] not in repr(result)


def test_invalid_provider_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="language"):
        GoogleNewsResearchProvider(None, CLOCK, "en?private")  # type: ignore[arg-type]
    seed = SOCIAL_SEEDS[0]
    with pytest.raises(ValueError, match="social RSS"):
        SocialFeedResearchProvider(
            None, CLOCK, replace(seed, spec=replace(seed.spec, category=Category.NEWS))
        )  # type: ignore[arg-type]

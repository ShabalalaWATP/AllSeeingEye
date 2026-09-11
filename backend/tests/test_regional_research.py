"""Regional collection routes explicitly and keeps question text off the network."""

from dataclasses import replace
from datetime import timedelta

import httpx
import pytest

from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.regional import REGIONAL_COUNTRIES, RegionalFeedResearchProvider
from ase.domain.research import CollectionStatus
from research_feed_helpers import CLOCK, QUERY, PublicFeed, item, rss

SEEDS = {seed.spec.id: seed for seed in REGIONAL_SEEDS}


@pytest.mark.parametrize("seed_id", SEEDS)
async def test_one_request_preserves_source_identity_and_excludes_article_text(
    monkeypatch: pytest.MonkeyPatch,
    seed_id: str,
) -> None:
    seed = SEEDS[seed_id]
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = RegionalFeedResearchProvider(feed.http, CLOCK, seed)
    query = replace(QUERY, languages=(seed.spec.language,), country_iso=REGIONAL_COUNTRIES[seed_id])
    result = await provider.collect(query)
    await feed.http.aclose()
    assert len(feed.requests) == len(feed.guarded) == 1
    assert str(feed.requests[0].url) == seed.spec.url
    assert query.question not in str(feed.requests[0].url)
    assert query.terms[0] not in str(feed.requests[0].url)
    assert result.attempts[0].status is CollectionStatus.COMPLETED
    event = result.items[0]
    assert event.source_id == f"research_regional_{seed_id}"
    assert event.language == seed.spec.language and event.grade == "F6"
    assert event.summary is None and event.point is None
    assert "headline" in result.attempts[0].explanation


@pytest.mark.parametrize("language", ["zh", "zh-CN", "zh-Hans"])
async def test_chinese_compatible_aliases(monkeypatch: pytest.MonkeyPatch, language: str) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = RegionalFeedResearchProvider(feed.http, CLOCK, SEEDS["cdt_zh"])
    assert provider.supports(replace(QUERY, languages=(language,), country_iso="CN"))
    assert not provider.supports(replace(QUERY, languages=("zh-Hant",), country_iso="CN"))
    await feed.http.aclose()


async def test_country_routes_without_discarding_deliberate_cross_region_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    provider = RegionalFeedResearchProvider(feed.http, CLOCK, SEEDS["meduza_ru"])
    query = replace(QUERY, languages=("ru",), country_iso="IR")
    assert not provider.supports(query)
    result = await provider.collect(query)
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED and not feed.requests
    assert provider.supports(replace(query, source_ids=(provider.id,)))
    assert provider.supports(replace(query, country_iso=None, country_isos=()))
    assert not provider.supports(replace(query, country_iso="RU", country_isos=(), terms=()))
    await feed.http.aclose()


async def test_only_title_matches_and_no_undated_or_out_of_window_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = rss(
        item("match")
        + item("old", date="2026-09-04T10:00:00Z")
        + item("undated", date="")
        + item("body-only", title="Unrelated heading")
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    result = await RegionalFeedResearchProvider(feed.http, CLOCK, SEEDS["hrana_en"]).collect(QUERY)
    await feed.http.aclose()
    assert [event.url for event in result.items] == ["https://publisher.example/match"]


async def test_research_iranwire_uses_newest_200_and_discloses_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = rss(
        "".join(
            item(str(i), date=(QUERY.since + timedelta(minutes=i)).isoformat()) for i in range(250)
        )
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    result = await RegionalFeedResearchProvider(feed.http, CLOCK, SEEDS["iranwire_en"]).collect(
        QUERY
    )
    await feed.http.aclose()
    assert len(result.items) == 200
    assert result.items[0].url == "https://publisher.example/249"
    assert result.items[-1].url == "https://publisher.example/50"
    assert result.items[0].attributes["feed_items_truncated"] is True


async def test_persian_matches_arabic_letter_variants_without_rewriting_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    title = "بررسی کیفیت آب"
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(title=title))))
    query = replace(QUERY, languages=("fa",), terms=("كيفيت",), country_iso="IR")
    result = await RegionalFeedResearchProvider(feed.http, CLOCK, SEEDS["hrana_fa"]).collect(query)
    await feed.http.aclose()
    assert len(result.items) == 1 and result.items[0].title == title


@pytest.mark.parametrize("status,payload", [(403, "blocked"), (200, "<html />"), (200, "<rss>")])
async def test_failure_is_not_empty_coverage(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    payload: str,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(status, text=payload))
    result = await RegionalFeedResearchProvider(feed.http, CLOCK, SEEDS["hrana_en"]).collect(QUERY)
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.FAILED


def test_unapproved_seed_cannot_become_regional_provider() -> None:
    seed = SEEDS["hrana_en"]
    with pytest.raises(ValueError, match="approved headline-only"):
        RegionalFeedResearchProvider(
            None, CLOCK, replace(seed, options=replace(seed.options, headlines_only=False))
        )  # type: ignore[arg-type]

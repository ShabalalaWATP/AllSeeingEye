"""Actual provider selection spends challenge budgets on targeted searches."""

from dataclasses import replace

import httpx
import pytest

from ase.container.research import research_service
from ase.domain.research import ResearchFocus
from research_feed_helpers import CLOCK, QUERY, PublicFeed, rss


@pytest.mark.parametrize(
    ("focus", "subject"),
    [(ResearchFocus.COMPANY, "CIK:123456"), (ResearchFocus.DOMAIN, "example.com")],
)
async def test_company_and_domain_challenges_do_not_repeat_registry_snapshots(
    monkeypatch: pytest.MonkeyPatch, focus: ResearchFocus, subject: str
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss("")))
    service = research_service(feed.http, CLOCK)
    queries = tuple(
        replace(QUERY, focus=focus, subject=subject, terms=(f"contrary claim {i}",))
        for i in range(6)
    )
    try:
        results = await service.challenge_many(queries)
    finally:
        await feed.http.aclose()
    assert len(feed.requests) == 6
    assert all(request.url.host == "news.google.com" for request in feed.requests)
    assert all(f"contrary claim {i}" in feed.requests[i].url.params["q"] for i in range(6))
    assert all(batch.attempts[0].source_id == "research_google_news_en" for batch in results)


@pytest.mark.parametrize("focus", [ResearchFocus.DOCUMENT, ResearchFocus.MEDIA])
async def test_private_challenges_have_no_public_provider_inventory(
    monkeypatch: pytest.MonkeyPatch, focus: ResearchFocus
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss("")))
    try:
        results = await research_service(feed.http, CLOCK).challenge_many(
            (replace(QUERY, focus=focus),)
        )
    finally:
        await feed.http.aclose()
    assert not feed.requests
    assert all(not batch.items for batch in results)

"""Google News RSS keyword collection using the existing bounded live-event pipeline.

No articles are fetched and no links are decoded during collection. The scheduler owns
timeouts, circuit breaking and publication; this connector reloads configuration and
reserves one request from its own budget before touching the upstream.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.rss import RssConnector, RssOptions
from ase.application.feeds.watchlists import WatchlistBudget, watchlist_terms
from ase.application.ports import Clock
from ase.application.ports.watchlists import WatchlistPlanStore
from ase.domain.events import Category, Event, Reliability
from ase.domain.sources import SourceKind, SourceSpec

SEARCH_URL = "https://news.google.com/rss/search"
SPEC = SourceSpec(
    id="google_news_watchlists",
    name="Google News watchlists",
    organisation="Google News",
    category=Category.NEWS,
    kind=SourceKind.RSS,
    url=SEARCH_URL,
    reliability=Reliability.C,
    poll_interval=timedelta(minutes=1),
    language="und",
    licence_note="Google News RSS, undocumented free feed; publisher rights apply.",
    homepage="https://news.google.com/",
)
OPTIONS = RssOptions(
    tags=frozenset({"watchlist", "google-news"}),
    rationale="Google News aggregator item; publisher independence is not yet verified",
)


def search_url(term: str) -> str:
    return (
        SEARCH_URL
        + "?"
        + urlencode({"q": f'"{term}" when:1d', "hl": "en-GB", "gl": "GB", "ceid": "GB:en"})
    )


class GoogleNewsWatchlistConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock, plans: WatchlistPlanStore) -> None:
        self._http = http
        self._clock = clock
        self._plans = plans
        self._budget = WatchlistBudget()
        self._failed = False

    async def fetch(self) -> list[Event]:
        terms = watchlist_terms(await self._plans.enabled_plans())
        term = self._budget.take(terms, self._clock.now())
        if term is None:
            if terms and self._failed:
                raise FeedFetchError("Google News watchlist is awaiting a retry")
            return []
        connector = RssConnector(
            self._http, self._clock, replace(SPEC, url=search_url(term)), OPTIONS
        )
        try:
            events = await connector.fetch()
        except Exception as exc:
            self._failed = True
            # Source health is shared with users; do not echo private plan terms from a URL.
            raise FeedFetchError("Google News watchlist request failed") from exc
        self._failed = False
        return events

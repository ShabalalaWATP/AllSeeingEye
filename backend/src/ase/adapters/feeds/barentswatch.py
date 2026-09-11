"""Optional regional AIS snapshot polling, admitted through the shared feed scheduler."""

import asyncio
from datetime import timedelta
from time import monotonic

from pydantic import SecretStr

from ase.adapters.feeds.barentswatch_http import LATEST_URL, BarentsWatchHttpClient
from ase.adapters.feeds.barentswatch_positions import COVERAGE, HOMEPAGE, SOURCE_ID, parse_positions
from ase.adapters.feeds.barentswatch_tokens import BarentsWatchTokens
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.secret_urls import protect_http_logs
from ase.application.ports import Clock
from ase.application.ports.feed_diagnostics import FeedDeferred
from ase.domain.events import Category, Event, Reliability
from ase.domain.source_ratings import SOURCE_RATING_POLICY_VERSION, SourceRating
from ase.domain.sources import SourceKind, SourceSpec

POLL_SECONDS = 120
FETCH_SECONDS = 45
SPEC = SourceSpec(
    id=SOURCE_ID,
    name="BarentsWatch AIS: Norwegian maritime zones",
    organisation="Norwegian Coastal Administration / BarentsWatch",
    category=Category.MARITIME,
    kind=SourceKind.API,
    url=LATEST_URL,
    homepage=HOMEPAGE,
    reliability=Reliability.F,
    poll_interval=timedelta(seconds=POLL_SECONDS),
    requires_key=True,
    instrument=True,
    licence_note="NLOD, Norwegian Coastal Administration. Data delivered by BarentsWatch. "
    "Normalised and freshness-filtered. https://www.barentswatch.no/en/articles/api-terms-and-conditions/",
    flags=frozenset({"ais", "regional_coverage", "reported_identity"}),
    rating=SourceRating(
        SOURCE_RATING_POLICY_VERSION,
        "unassessed",
        None,
        "Official receiver aggregation does not verify a vessel's broadcast identity or position.",
        COVERAGE,
        (
            "AIS identity, type and position may be wrong or spoofed; coverage is incomplete.",
            "Fishing vessels under 15 metres and leisure/sailing vessels under 45 metres "
            "are excluded.",
            "Combined records do not provide a separate static vessel-type observation time.",
        ),
        "aggregator",
        False,
    ),
)


class BarentsWatchConnector:
    spec = SPEC

    def __init__(
        self,
        http: BarentsWatchHttpClient,
        clock: Clock,
        client_id: SecretStr,
        client_secret: SecretStr,
    ) -> None:
        self._http, self._clock = http, clock
        self._tokens = BarentsWatchTokens(http, client_id, client_secret)
        self._lock = asyncio.Lock()
        self._next_poll = 0.0

    async def fetch(self) -> list[Event]:
        with protect_http_logs():
            try:
                async with asyncio.timeout(FETCH_SECONDS), self._lock:
                    now = monotonic()
                    if now < self._next_poll:
                        raise FeedDeferred(
                            "BarentsWatch snapshot cooldown active.",
                            self._clock.now() + timedelta(seconds=self._next_poll - now),
                        )
                    self._next_poll = now + POLL_SECONDS
                    credential = await self._tokens.credential()
                    try:
                        data = await self._http.get_json(LATEST_URL, credential=credential)
                    except Exception:
                        self._tokens.invalidate(credential)
                        raise
                    return parse_positions(data, self._clock.now())
            except FeedDeferred:
                raise
            except Exception:
                raise FeedFetchError("BarentsWatch snapshot request failed.") from None

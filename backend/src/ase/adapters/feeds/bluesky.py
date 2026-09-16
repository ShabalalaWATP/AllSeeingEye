"""Bluesky public AppView: author feeds for a reviewed list of public accounts.

Public API only. There is no login, token or cookie, `app.bsky.feed.searchPosts` answers
403 without a session and is not used, and `public.api.bsky.app/robots.txt` allows
crawling the public API while asking callers to back off on HTTP 429. Each poll reads a
bounded slice of the registry so a full sweep is spread over several cycles, and the
shared per-host pacer keeps this process to one request at a time against the host.

Posts are social listening at doctrine's floor (reliability E, credibility 6) until
something corroborates them, whoever the account belongs to.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Final

from ase.adapters.feeds.bluesky_accounts import ACCOUNTS, BlueskyAccount
from ase.adapters.feeds.bluesky_posts import to_event
from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import Category, Event, Reliability
from ase.domain.sources import SourceKind, SourceSpec

HOST: Final = "public.api.bsky.app"
AUTHOR_FEED: Final = f"https://{HOST}/xrpc/app.bsky.feed.getAuthorFeed"
# The author's own posts and their own threads; other people's replies never arrive.
FILTER: Final = "posts_and_author_threads"
POSTS_PER_ACCOUNT: Final = 15
ACCOUNTS_PER_CYCLE: Final = 10
MAX_ITEMS: Final = 50
POLL_INTERVAL: Final = timedelta(minutes=15)
LICENCE_NOTE: Final = (
    "Bluesky public AppView; robots.txt allows crawling the public API. Bounded post "
    "excerpts, handles, times and post links only; no media, no logged-in content"
)

SPEC: Final = SourceSpec(
    id="bluesky_curated",
    name="Bluesky curated accounts",
    organisation="Bluesky",
    category=Category.SOCIAL,
    kind=SourceKind.API,
    url=AUTHOR_FEED,
    reliability=Reliability.E,
    poll_interval=POLL_INTERVAL,
    licence_note=LICENCE_NOTE,
    homepage="https://bsky.app/",
    language="und",
)


def author_feed_url(handle: str, limit: int = POSTS_PER_ACCOUNT) -> str:
    return f"{AUTHOR_FEED}?actor={handle}&limit={limit}&filter={FILTER}"


class BlueskyConnector:
    """Reads `ACCOUNTS_PER_CYCLE` curated accounts per poll, rotating through the registry."""

    spec = SPEC

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        accounts: tuple[BlueskyAccount, ...] = ACCOUNTS,
        *,
        per_cycle: int = ACCOUNTS_PER_CYCLE,
    ) -> None:
        if not accounts:
            raise ValueError("The Bluesky connector needs at least one reviewed account")
        if not 1 <= per_cycle <= len(accounts):
            raise ValueError("Invalid Bluesky accounts-per-cycle bound")
        self._http, self._clock = http, clock
        self._accounts, self._per_cycle = accounts, per_cycle
        self._cursor = 0

    @property
    def requests_per_hour(self) -> float:
        """The polling load this connector introduces against one host."""
        return self._per_cycle * 3600 / POLL_INTERVAL.total_seconds()

    def _slice(self) -> tuple[BlueskyAccount, ...]:
        total = len(self._accounts)
        start = self._cursor % total
        selected = tuple(self._accounts[(start + step) % total] for step in range(self._per_cycle))
        self._cursor = (start + self._per_cycle) % total
        return selected

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        events: dict[str, Event] = {}
        failures: list[Exception] = []
        attempted = 0
        for account in self._slice():
            attempted += 1
            try:
                payload = await self._http.get_json(author_feed_url(account.handle))
            except NotModified:
                continue
            except Exception as exc:
                # One account's failure must not end the cycle for the other nine.
                failures.append(exc)
                continue
            for event in self._events(payload, account, now):
                events.setdefault(event.id, event)
        if failures and len(failures) == attempted:
            # Every account in this cycle failed: the source is unhealthy, not quiet.
            raise failures[-1]
        return list(events.values())

    def _events(self, payload: Any, account: BlueskyAccount, now: datetime) -> list[Event]:
        feed = payload.get("feed") if isinstance(payload, dict) else None
        if not isinstance(feed, list):
            return []
        mapped = (to_event(item, account, self.spec, now) for item in feed[:MAX_ITEMS])
        return [event for event in mapped if event is not None]

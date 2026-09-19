"""Minimum spacing between request starts to one upstream host, across every connector.

Several connectors share one community API (adsb.lol serves the military, LADD, PIA,
emergency, watched-area, viewport and worldwide-sweep feeds). Each paces itself, but
together they started within the same few seconds after a restart and the provider
answered HTTP 429. One shared, per-host gap keeps this process within polite limits.

The YouTube Data API is here for the same reason: every watched channel is polled
through one host under one project quota, and the scheduler only spreads first polls
across five seconds. The per-host gap is the floor beneath that spread.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import timedelta
from urllib.parse import urlsplit

from ase.adapters.feeds.http_contracts import MAX_RETRY_AFTER, FeedRateLimitedError

ADSB_LOL_HOST = "api.adsb.lol"
# Telegram serves every curated channel preview from one host, and the pages are large
# and uncacheable. Five seconds between them keeps this process well inside polite use.
TELEGRAM_HOST = "t.me"
# The Bluesky public AppView serves the rotating curated-account poll and the on-demand
# research route. Its robots.txt asks for a handful of concurrent requests at most.
BLUESKY_HOST = "public.api.bsky.app"
# The YouTube Data API, used only when the operator has configured a key.
GOOGLE_APIS_HOST = "www.googleapis.com"
DEFAULT_HOST_INTERVALS: Mapping[str, float] = {
    ADSB_LOL_HOST: 1.0,
    TELEGRAM_HOST: 5.0,
    BLUESKY_HOST: 1.0,
    GOOGLE_APIS_HOST: 1.0,
}


class HostPacer:
    def __init__(
        self,
        intervals: Mapping[str, float],
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if any(value <= 0 or value > 60 for value in intervals.values()):
            raise ValueError("Host request spacing must be between 0 and 60 seconds.")
        self._intervals = {host.lower(): value for host, value in intervals.items()}
        self._monotonic, self._sleep = monotonic, sleep
        self._locks: dict[str, asyncio.Lock] = {}
        self._next_start: dict[str, float] = {}
        self._cooldowns: dict[str, float] = {}

    def rate_limited(self, url: str, retry_after: timedelta | None) -> None:
        """Share a bounded throttle across configured hosts' connectors only."""
        host = (urlsplit(url).hostname or "").lower()
        if host not in self._intervals:
            return
        requested = retry_after if retry_after is not None else timedelta(seconds=60)
        wait = min(max(requested, timedelta(seconds=1)), MAX_RETRY_AFTER)
        self._cooldowns[host] = max(
            self._cooldowns.get(host, 0.0), self._monotonic() + wait.total_seconds()
        )

    def _check_cooldown(self, host: str, url: str) -> None:
        remaining = self._cooldowns.get(host, 0.0) - self._monotonic()
        if remaining > 0:
            # Return control to the scheduler instead of consuming a batch's timeout.
            raise FeedRateLimitedError(url, timedelta(seconds=remaining))
        self._cooldowns.pop(host, None)

    async def wait(self, url: str) -> None:
        """Wait until this host's next request slot; unlisted hosts are not delayed."""
        host = (urlsplit(url).hostname or "").lower()
        interval = self._intervals.get(host)
        if interval is None:
            return
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            self._check_cooldown(host, url)
            delay = self._next_start.get(host, 0.0) - self._monotonic()
            if delay > 0:
                await self._sleep(delay)
                self._check_cooldown(host, url)
            self._next_start[host] = self._monotonic() + interval

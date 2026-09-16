"""Minimum spacing between request starts to one upstream host, across every connector.

Several connectors share one community API (adsb.lol serves the military, LADD, PIA,
emergency, watched-area, viewport and worldwide-sweep feeds). Each paces itself, but
together they started within the same few seconds after a restart and the provider
answered HTTP 429. One shared, per-host gap keeps this process within polite limits.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from urllib.parse import urlsplit

ADSB_LOL_HOST = "api.adsb.lol"
# The Bluesky public AppView serves the rotating curated-account poll and the on-demand
# research route. Its robots.txt asks for a handful of concurrent requests at most.
BLUESKY_HOST = "public.api.bsky.app"
DEFAULT_HOST_INTERVALS: Mapping[str, float] = {ADSB_LOL_HOST: 1.0, BLUESKY_HOST: 1.0}


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

    async def wait(self, url: str) -> None:
        """Wait until this host's next request slot; unlisted hosts are not delayed."""
        host = (urlsplit(url).hostname or "").lower()
        interval = self._intervals.get(host)
        if interval is None:
            return
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            delay = self._next_start.get(host, 0.0) - self._monotonic()
            if delay > 0:
                await self._sleep(delay)
            self._next_start[host] = self._monotonic() + interval

"""Read-only publisher checks using the production HTTP guard and RSS parser.

The result contains counts and dates, never article text, titles or request headers.
One instance is sequential: a response hook records only its current HTTP status.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

import httpx

from ase.adapters.feeds.host_pacing import HostPacer
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.adapters.tls import verified_ssl_context
from ase.application.ports import Clock
from ase.domain.events import Event


@dataclass(frozen=True, slots=True)
class ProbeResult:
    source_id: str
    url: str
    observed_at: datetime
    http_status: int | None
    item_count: int
    newest_publication: datetime | None
    error: str | None = None


class RosterProbe:
    """Bounded, sequential live probes; transport injection is for offline fixtures only."""

    def __init__(
        self,
        clock: Clock,
        seeds: Sequence[RssSeed],
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._clock = clock
        self._status: int | None = None
        client = httpx.AsyncClient(
            verify=verified_ssl_context(),
            follow_redirects=False,
            timeout=30.0,
            transport=transport,
            event_hooks={"response": [self._response]},
        )
        hosts = {urlsplit(seed.spec.url).hostname or "": 1.0 for seed in seeds}
        self._http = FeedHttpClient(
            "TheAllSeeingEye/0.1 publisher-feed-verification",
            client=client,
            total_timeout_seconds=60,
            host_pacer=HostPacer(hosts),
        )

    async def _response(self, response: httpx.Response) -> None:
        self._status = response.status_code

    async def fetch(self, seed: RssSeed) -> tuple[ProbeResult, list[Event]]:
        self._status = None
        error = None
        events: list[Event] = []
        try:
            events = await RssConnector(self._http, self._clock, seed.spec, seed.options).fetch()
        except Exception as exc:
            # Fixed local class names only. Upstream bodies, URLs and exceptions are untrusted.
            error = type(exc).__name__
        dates = [event.published_at for event in events if event.published_at is not None]
        return (
            ProbeResult(
                seed.spec.id,
                seed.spec.url,
                self._clock.now(),
                self._status,
                len(events),
                max(dates, default=None),
                error,
            ),
            events,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

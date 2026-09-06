"""One origin-bound credential and rolling allowance shared by UK registry tasks."""

import asyncio
import base64
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedCredential, FeedHttpClient
from ase.adapters.research_records.records import receipt
from ase.application.ports import Clock
from ase.domain.events import Event
from ase.domain.research import CollectionStatus, ResearchBatch

ORIGIN = "https://api.company-information.service.gov.uk"
REQUEST_ALLOWANCE = 600


class CompaniesHouseClient:
    def __init__(self, http: FeedHttpClient, clock: Clock, api_key: str | None = None) -> None:
        self._http, self._clock = http, clock
        self.requests: deque[datetime] = deque()
        self._credential: FeedCredential | None = None
        if api_key:
            if (
                len(api_key) > 512
                or ":" in api_key
                or any(ord(char) < 33 or ord(char) > 126 for char in api_key)
            ):
                raise ValueError("Invalid Companies House API key configuration.")
            encoded = base64.b64encode(f"{api_key}:".encode("ascii")).decode("ascii")
            self._credential = FeedCredential(ORIGIN, f"Basic {encoded}")

    async def collect(
        self,
        source_id: str,
        name: str,
        url: str,
        parse: Callable[[Any], list[Event]],
        limitations: str,
    ) -> ResearchBatch:
        if self._credential is None:
            return receipt(
                source_id,
                name,
                CollectionStatus.UNAVAILABLE,
                "A Companies House API key is not configured; no request was made.",
            )
        now = self._clock.now()
        while self.requests and self.requests[0] <= now - timedelta(minutes=5):
            self.requests.popleft()
        if len(self.requests) >= REQUEST_ALLOWANCE:
            return receipt(
                source_id,
                name,
                CollectionStatus.BUDGET_EXHAUSTED,
                "The local Companies House request allowance is exhausted; no request was made.",
            )
        self.requests.append(now)
        try:
            async with asyncio.timeout(20):
                payload = await self._http.get_json(url, credential=self._credential)
            items = parse(payload)
        except TimeoutError:
            return receipt(
                source_id,
                name,
                CollectionStatus.TIMED_OUT,
                "The Companies House request timed out; no retry was made.",
            )
        except Exception:
            # Do not disclose credential, response body or private query in errors.
            return receipt(
                source_id,
                name,
                CollectionStatus.FAILED,
                "Companies House returned no usable response; no retry was made.",
            )
        return receipt(
            source_id,
            name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            limitations,
            items,
        )

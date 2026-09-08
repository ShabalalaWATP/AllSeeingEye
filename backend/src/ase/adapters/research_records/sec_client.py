"""Shared SEC pacing over DNS-pinned, size-bounded HTTP; no redirects or credentials."""

import asyncio
import json
import re
from typing import Any

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified


class SecClient:
    def __init__(self, http: FeedHttpClient) -> None:
        self.http = http
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    def require_configured(self) -> None:
        agent = self.http.user_agent
        if (
            not re.search(r"[^\s@()]+@[^\s@()]+\.[A-Za-z]{2,}", agent)
            or ".invalid" in agent
            or "set-ASE_" in agent
        ):
            raise FeedFetchError(
                "Configure ASE_FEEDS_CONTACT with the operator's real contact email "
                "before SEC access."
            )

    async def get_bytes(self, url: str) -> bytes:
        self.require_configured()
        if not re.fullmatch(
            r"https://(?:data\.sec\.gov/submissions/[A-Za-z0-9.-]+\.json|"
            r"www\.sec\.gov/(?:files/company_tickers\.json|"
            r"Archives/edgar/data/[0-9]+/[0-9]{18}/[A-Za-z0-9_.-]+))",
            url,
        ):
            raise FeedFetchError("Unsupported SEC data resource.")
        async with self._lock:
            loop = asyncio.get_running_loop()
            await asyncio.sleep(max(0, self._last_request + 0.25 - loop.time()))
            self._last_request = loop.time()
            try:
                return await self.http.get_bytes(url, conditional=False, max_redirects=0)
            except NotModified:
                # These requests have no conditional cache or previous body to reuse.
                raise FeedFetchError("SEC returned an unexpected unchanged response.") from None

    async def get_json(
        self, url: str, *, conditional: bool = False, max_redirects: int = 0
    ) -> dict[str, Any]:
        data = json.loads(await self.get_bytes(url))
        if not isinstance(data, dict):
            raise ValueError("SEC response is not an object")
        return data

"""Request-local OpenAQ authentication and a shared, conservative request allowance."""

import asyncio
import json
from collections import deque
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from ase.adapters.feeds.http import FeedCredential, FeedHttpClient
from ase.adapters.feeds.secret_urls import protect_http_logs

ORIGIN = "https://api.openaq.org"
MAX_BODY_BYTES = 1024 * 1024
REQUEST_SPACING = 2.0
HOURLY_ALLOWANCE = 1800
FAILURE_COOLDOWN = 60.0


class OpenAqAllowanceError(Exception):
    """The local hourly allowance or a failure cooldown prevents another request."""


class OpenAqClient:
    def __init__(
        self,
        http: FeedHttpClient,
        api_key: str | None,
        *,
        timer: Callable[[], float] = monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._http, self._timer, self._sleep = http, timer, sleep
        self._lock = asyncio.Lock()
        self._requests: deque[float] = deque()
        self._cooldown_until = 0.0
        self._credential = None
        if api_key:
            if len(api_key) > 512 or any(ord(char) < 33 or ord(char) > 126 for char in api_key):
                raise ValueError("Invalid OpenAQ API key configuration.")
            self._credential = FeedCredential(ORIGIN, api_key, header_name="X-API-Key")

    @property
    def configured(self) -> bool:
        return self._credential is not None

    async def _admit(self) -> None:
        # Reused by every research run in this process. Failed/cancelled requests count.
        async with self._lock:
            now = self._timer()
            if now < self._cooldown_until:
                raise OpenAqAllowanceError()
            if self._requests:
                await self._sleep(max(0.0, self._requests[-1] + REQUEST_SPACING - now))
            now = self._timer()
            while self._requests and self._requests[0] <= now - 3600:
                self._requests.popleft()
            if len(self._requests) >= HOURLY_ALLOWANCE or now < self._cooldown_until:
                raise OpenAqAllowanceError()
            self._requests.append(now)

    async def get(self, path: str) -> Any:
        if self._credential is None:
            raise ValueError("OpenAQ is not configured.")
        # Callers construct fixed endpoint paths from validated integer identifiers.
        url = ORIGIN + path
        self._credential.require_origin(url)
        await self._admit()
        with protect_http_logs():
            try:
                body = await self._http.get_bytes(url, credential=self._credential)
                if len(body) > MAX_BODY_BYTES:
                    raise ValueError("OpenAQ response exceeds its admission bound.")
                return json.loads(body)
            except Exception:
                # Includes HTTP 429/auth errors without inspecting or exposing the body.
                self._cooldown_until = self._timer() + FAILURE_COOLDOWN
                raise

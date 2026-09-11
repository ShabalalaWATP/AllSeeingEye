"""In-memory OAuth client-credentials token cache with coalesced, bounded refreshes."""

import asyncio
import re
from time import monotonic

from pydantic import SecretStr

from ase.adapters.feeds.barentswatch_http import (
    LIVE_ORIGIN,
    REQUEST_SECONDS,
    BarentsWatchHttpClient,
)
from ase.adapters.feeds.http import FeedCredential, FeedFetchError

RETRY_SECONDS = 120
EXPIRY_MARGIN_SECONDS = 30
MAX_TOKEN_LIFETIME_SECONDS = 3600


class BarentsWatchTokens:
    def __init__(
        self, http: BarentsWatchHttpClient, client_id: SecretStr, client_secret: SecretStr
    ) -> None:
        self._http, self._client_id, self._client_secret = http, client_id, client_secret
        self._lock = asyncio.Lock()
        self._credential: FeedCredential | None = None
        self._expires_at = 0.0
        self._retry_at = 0.0

    async def credential(self) -> FeedCredential:
        try:
            async with asyncio.timeout(REQUEST_SECONDS), self._lock:
                now = monotonic()
                if self._credential is not None and now < self._expires_at:
                    return self._credential
                self._credential = None
                if now < self._retry_at:
                    raise FeedFetchError("BarentsWatch authentication cooldown active.")
                # Failed or cancelled attempts consume the same bounded request budget.
                self._retry_at = now + RETRY_SECONDS
                data = await self._http.token(self._client_id, self._client_secret)
                if not isinstance(data, dict):
                    raise ValueError
                token, expires = data.get("access_token"), data.get("expires_in")
                if (
                    not isinstance(token, str)
                    or not 1 <= len(token) <= 8185
                    or re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token) is None
                    or not isinstance(data.get("token_type"), str)
                    or data["token_type"].lower() != "bearer"
                    or type(expires) is not int
                    or not 60 <= expires <= 86400
                    or data.get("scope", "ais") != "ais"
                ):
                    raise ValueError
                self._expires_at = (
                    now + min(expires, MAX_TOKEN_LIFETIME_SECONDS) - EXPIRY_MARGIN_SECONDS
                )
                self._credential = FeedCredential(LIVE_ORIGIN, f"Bearer {token}")
                return self._credential
        except Exception:
            raise FeedFetchError("BarentsWatch authentication unavailable.") from None

    def invalidate(self, credential: FeedCredential) -> None:
        """Never let an older failed request invalidate a newer refreshed token."""
        if self._credential is credential:
            self._credential = None

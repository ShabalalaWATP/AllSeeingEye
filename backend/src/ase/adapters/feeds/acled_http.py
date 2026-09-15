"""Fixed-origin ACLED transport: the OAuth refresh form POST and bearer reads that expose 401.

The shared authenticated GET deliberately hides status codes. ACLED needs to tell an
expired access token (refresh once and retry) from every other failure, so this client
issues its own bounded requests and still never retains tokens or response bodies.
"""

import asyncio
import json
from typing import Any

import httpx
from pydantic import SecretStr

from ase.adapters.feeds.http import (
    FeedCredential,
    FeedFetchError,
    FeedHttpClient,
    assert_public_host,
)
from ase.adapters.feeds.secret_urls import protect_http_logs

ORIGIN = "https://acleddata.com"
TOKEN_URL = f"{ORIGIN}/oauth/token"
CLIENT_ID = "acled"
TOKEN_MAX_BYTES = 64 * 1024
DATA_MAX_BYTES = 5 * 1024 * 1024
TOKEN_SECONDS = 20
READ_SECONDS = 45
MAX_SECRET_CHARS = 8192


class AcledUnauthorised(FeedFetchError):
    """ACLED refused the bearer token; the caller may refresh it once."""


class AcledForbidden(FeedFetchError):
    """ACLED accepted the token but the account tier has no API data access."""


class AcledRefreshRejected(FeedFetchError):
    """The token endpoint refused the refresh token itself (expired, revoked or malformed)."""


class AcledHttpClient(FeedHttpClient):
    def __init__(self, user_agent: str, *, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(
            user_agent,
            max_bytes=DATA_MAX_BYTES,
            client=client
            or httpx.AsyncClient(timeout=READ_SECONDS, follow_redirects=False, trust_env=False),
        )

    async def refresh(self, refresh_token: SecretStr) -> Any:
        """Exchange a refresh token in a bounded form body sent only to the fixed origin."""
        with protect_http_logs():
            try:
                async with asyncio.timeout(TOKEN_SECONDS):
                    value = refresh_token.get_secret_value()
                    if (
                        not value.strip()
                        or len(value) > MAX_SECRET_CHARS
                        or any(ord(char) <= 32 or ord(char) == 127 for char in value)
                    ):
                        raise AcledRefreshRejected("ACLED refresh token is malformed.")
                    address = await assert_public_host(TOKEN_URL)
                    headers = {"Accept-Encoding": "identity", "Accept": "application/json"}
                    target, extensions = self._pinned(TOKEN_URL, address, headers)
                    async with self._client.stream(
                        "POST",
                        target,
                        data={
                            "refresh_token": value,
                            "grant_type": "refresh_token",
                            "client_id": CLIENT_ID,
                        },
                        headers=headers,
                        extensions=extensions,
                        follow_redirects=False,
                    ) as response:
                        if response.status_code in (400, 401):
                            raise AcledRefreshRejected("ACLED refused the refresh token.")
                        if response.status_code != 200:
                            raise ValueError
                        return json.loads(await _read_limited(response, TOKEN_MAX_BYTES))
            except AcledRefreshRejected:
                raise AcledRefreshRejected("ACLED refused the refresh token.") from None
            except Exception:
                raise FeedFetchError("ACLED authentication failed.") from None

    async def read_json(self, url: str, credential: FeedCredential) -> Any:
        """One bearer GET without redirects; only 401 and 403 are reported to the caller."""
        credential.require_origin(url)
        with protect_http_logs():
            try:
                async with asyncio.timeout(READ_SECONDS):
                    address = await assert_public_host(url)
                    headers = {
                        "Accept-Encoding": "identity",
                        "Accept": "application/json",
                        credential.header_name: credential.authorization,
                    }
                    target, extensions = self._pinned(url, address, headers)
                    async with self._client.stream(
                        "GET",
                        target,
                        headers=headers,
                        extensions=extensions,
                        follow_redirects=False,
                    ) as response:
                        if response.status_code == 401:
                            raise AcledUnauthorised("ACLED refused the access token.")
                        if response.status_code == 403:
                            raise AcledForbidden("ACLED refused data access for this account.")
                        if response.status_code != 200:
                            raise ValueError
                        return json.loads(await _read_limited(response, DATA_MAX_BYTES))
            except AcledUnauthorised:
                raise AcledUnauthorised("ACLED refused the access token.") from None
            except AcledForbidden:
                raise AcledForbidden("ACLED refused data access for this account.") from None
            except Exception:
                raise FeedFetchError("Authenticated feed request failed.") from None


async def _read_limited(response: httpx.Response, limit: int) -> bytes:
    if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
        raise ValueError
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise ValueError
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > limit:
            raise ValueError
        chunks.append(chunk)
    return b"".join(chunks)

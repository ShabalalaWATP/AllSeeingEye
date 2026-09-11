"""Fixed-origin BarentsWatch transport, including its guarded OAuth form POST."""

import asyncio
import json
from typing import Any

import httpx
from pydantic import SecretStr

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, assert_public_host
from ase.adapters.feeds.secret_urls import protect_http_logs

TOKEN_URL = "https://id.barentswatch.no/connect/token"  # noqa: S105
LIVE_ORIGIN = "https://live.ais.barentswatch.no"
LATEST_URL = f"{LIVE_ORIGIN}/v1/latest/combined"
TOKEN_MAX_BYTES = 64 * 1024
SNAPSHOT_MAX_BYTES = 5 * 1024 * 1024
REQUEST_SECONDS = 20
MAX_SECRET_CHARS = 2048


class BarentsWatchHttpClient(FeedHttpClient):
    def __init__(self, user_agent: str, *, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(
            user_agent,
            max_bytes=SNAPSHOT_MAX_BYTES,
            client=client
            or httpx.AsyncClient(timeout=REQUEST_SECONDS, follow_redirects=False, trust_env=False),
        )

    async def token(self, client_id: SecretStr, client_secret: SecretStr) -> Any:
        """Send credentials only in a bounded body to the fixed, DNS-pinned identity origin."""
        with protect_http_logs():
            try:
                async with asyncio.timeout(REQUEST_SECONDS):
                    values = (client_id.get_secret_value(), client_secret.get_secret_value())
                    if any(
                        not value.strip()
                        or len(value) > MAX_SECRET_CHARS
                        or any(ord(char) < 32 or ord(char) == 127 for char in value)
                        for value in values
                    ):
                        raise ValueError
                    address = await assert_public_host(TOKEN_URL)
                    headers = {"Accept-Encoding": "identity", "Accept": "application/json"}
                    target, extensions = self._pinned(TOKEN_URL, address, headers)
                    async with self._client.stream(
                        "POST",
                        target,
                        data={
                            "client_id": values[0],
                            "client_secret": values[1],
                            "scope": "ais",
                            "grant_type": "client_credentials",
                        },
                        headers=headers,
                        extensions=extensions,
                        follow_redirects=False,
                    ) as response:
                        if response.status_code != 200:
                            raise ValueError
                        return json.loads(await _read_token(response))
            except Exception:
                raise FeedFetchError("BarentsWatch authentication failed.") from None


async def _read_token(response: httpx.Response) -> bytes:
    if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
        raise ValueError
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > TOKEN_MAX_BYTES:
        raise ValueError
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > TOKEN_MAX_BYTES:
            raise ValueError
        chunks.append(chunk)
    return b"".join(chunks)

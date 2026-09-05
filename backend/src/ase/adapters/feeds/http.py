"""Outbound HTTP for connectors: size caps, timeouts, conditional requests, no private hosts."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3


class FeedFetchError(Exception):
    """Any failure fetching a feed; the message is safe to show to an administrator."""


class NotModified(Exception):
    """The upstream answered 304: nothing new since the last poll (an outcome, not a fault)."""


@dataclass(slots=True)
class _Validators:
    etag: str | None = None
    last_modified: str | None = None


def is_public_address(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True  # a hostname; resolved and checked separately
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


async def assert_public_host(url: str) -> None:
    """Refuse URLs whose host resolves to private, loopback or link-local space (SSRF guard)."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FeedFetchError(f"Unsupported URL: {url}")
    if parts.username or parts.password:
        raise FeedFetchError("Credentials in feed URLs are not allowed")
    host = parts.hostname
    if not is_public_address(host):
        raise FeedFetchError(f"Refusing to fetch a non-public address: {host}")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FeedFetchError(f"Cannot resolve {host}") from exc
    for info in infos:
        if not is_public_address(str(info[4][0])):
            raise FeedFetchError(f"Refusing to fetch {host}: resolves to a non-public address")


class FeedHttpClient:
    def __init__(
        self,
        user_agent: str,
        *,
        timeout_seconds: float = 30.0,
        max_bytes: int = DEFAULT_MAX_BYTES,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._validators: dict[str, _Validators] = {}
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds), follow_redirects=False
        )
        # Polite identification is required by most upstreams, whichever transport is used.
        self._client.headers["User-Agent"] = user_agent
        self._client.headers["Accept"] = "application/json, text/*;q=0.8, */*;q=0.5"

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_bytes(self, url: str, *, conditional: bool = True) -> bytes:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            await assert_public_host(current)
            headers: dict[str, str] = {}
            validators = self._validators.get(url) if conditional else None
            if validators and validators.etag:
                headers["If-None-Match"] = validators.etag
            if validators and validators.last_modified:
                headers["If-Modified-Since"] = validators.last_modified
            try:
                async with self._client.stream("GET", current, headers=headers) as response:
                    if response.status_code == 304:
                        raise NotModified(url)
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FeedFetchError("Redirect without a location")
                        current = str(response.url.join(location))
                        continue
                    if response.status_code >= 400:
                        raise FeedFetchError(f"HTTP {response.status_code} from {current}")
                    body = await self._read_bounded(response)
            except httpx.HTTPError as exc:
                raise FeedFetchError(f"{type(exc).__name__}: {exc}") from exc
            if conditional:
                self._validators[url] = _Validators(
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
            return body
        raise FeedFetchError("Too many redirects")

    async def get_json(self, url: str, *, conditional: bool = True) -> Any:
        try:
            return json.loads(await self.get_bytes(url, conditional=conditional))
        except ValueError as exc:
            raise FeedFetchError(f"Invalid JSON from {url}") from exc

    async def get_text(self, url: str, *, conditional: bool = True) -> str:
        return (await self.get_bytes(url, conditional=conditional)).decode("utf-8", "replace")

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > self._max_bytes:
            raise FeedFetchError(f"Response too large ({declared} bytes)")
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self._max_bytes:
                raise FeedFetchError(f"Response exceeded {self._max_bytes} bytes")
            chunks.append(chunk)
        return b"".join(chunks)

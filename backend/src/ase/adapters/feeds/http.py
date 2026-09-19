"""Bounded feed HTTP with shared host throttling and conditional requests.

SSRF checks resolve every address, then pin the connection to a checked public address
while retaining the original Host header and TLS name, closing DNS rebinding gaps.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from collections import OrderedDict
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from ase.adapters.feeds.bounded_gzip import BoundedGzipError, read_feed_response
from ase.adapters.feeds.host_pacing import HostPacer
from ase.adapters.feeds.http_contracts import (
    FeedCredential,
    FeedFetchError,
    FeedHttpStatusError,
    FeedRateLimitedError,
    FeedTimeoutError,
    FeedValidators,
    NotModified,
    classify_fetch_error,
    safe_header_token,
    status_error,
)
from ase.adapters.feeds.secret_urls import SecretFeedUrl, protect_http_logs
from ase.application.feeds.poll_scope import active_poll_scope

__all__ = [
    "FeedCredential",
    "FeedFetchError",
    "FeedHttpClient",
    "FeedHttpStatusError",
    "FeedTimeoutError",
    "NotModified",
    "assert_public_host",
    "classify_fetch_error",
    "is_public_address",
    "pin_url",
]

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
MAX_VALIDATORS = 256
_TRANSLATION_PREFIXES = (
    ipaddress.IPv6Network("64:ff9b::/96"),
    ipaddress.IPv6Network("64:ff9b:1::/48"),
)


def is_public_address(host: str) -> bool:
    """Only globally routable addresses; shared CGNAT space (100.64.0.0/10) is not global."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True  # a hostname; resolved and checked separately
    if isinstance(address, ipaddress.IPv6Address) and (
        address.ipv4_mapped is not None
        or address.sixtofour is not None
        or address.teredo is not None
        or any(address in prefix for prefix in _TRANSLATION_PREFIXES)
    ):
        return False
    return bool(
        address.is_global
        and not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )
    )


async def assert_public_host(url: str) -> str | None:
    """Refuse URLs whose host resolves to private space; return the address to connect to.

    Returns None for a literal public IP address (nothing to pin) and raises on any
    private, loopback or link-local answer. Callers must connect to the returned address
    rather than resolving again, which is what closes the DNS rebinding window.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FeedFetchError(f"Unsupported URL: {url}")
    if parts.username or parts.password:
        raise FeedFetchError("Credentials in feed URLs are not allowed")
    host = parts.hostname
    if not is_public_address(host):
        raise FeedFetchError(f"Refusing to fetch a non-public address: {host}")
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FeedFetchError(f"Cannot resolve {host}") from exc
    addresses = [str(info[4][0]) for info in infos]
    for address in addresses:
        if not is_public_address(address):
            raise FeedFetchError(f"Refusing to fetch {host}: resolves to a non-public address")
    if not addresses:
        raise FeedFetchError(f"Cannot resolve {host}")
    return addresses[0]


def pin_url(url: str, address: str) -> str:
    """The same URL with the host replaced by the address that was checked."""
    parts = urlsplit(url)
    literal = f"[{address}]" if ":" in address else address
    netloc = literal if parts.port is None else f"{literal}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class FeedHttpClient:
    def __init__(
        self,
        user_agent: str,
        *,
        timeout_seconds: float = 30.0,
        total_timeout_seconds: float = 120.0,
        max_bytes: int = DEFAULT_MAX_BYTES,
        client: httpx.AsyncClient | None = None,
        host_pacer: HostPacer | None = None,
    ) -> None:
        if client is not None and (
            client.auth is not None
            or any(
                name in client.headers
                for name in ("authorization", "x-ucdp-access-token", "x-api-key")
            )
        ):
            raise ValueError("Shared feed clients must not carry global authorisation.")
        self._max_bytes, self._pacer = max_bytes, host_pacer or HostPacer({})
        if total_timeout_seconds <= 0:
            raise ValueError("The total feed timeout must be positive.")
        self._total_timeout_seconds = total_timeout_seconds
        self._validators: OrderedDict[str, FeedValidators] = OrderedDict()
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds), follow_redirects=False
        )
        # Polite identification is required by most upstreams, whichever transport is used.
        self._client.headers["User-Agent"] = user_agent
        self._client.headers["Accept"] = "application/json, text/*;q=0.8, */*;q=0.5"

    @property
    def user_agent(self) -> str:
        return str(self._client.headers.get("User-Agent", ""))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_secret_bytes(self, target: SecretFeedUrl) -> bytes:
        """No redirects, URL cache or diagnostics for keys embedded in upstream paths."""
        with protect_http_logs():
            try:
                return await self.get_bytes(target.url, conditional=False, max_redirects=0)
            except Exception:
                # Scheduler health and tracebacks must not retain upstream text or URL.
                raise FeedFetchError("Protected feed request failed.") from None

    async def get_bytes(
        self,
        url: str,
        *,
        conditional: bool = True,
        max_redirects: int = MAX_REDIRECTS,
        credential: FeedCredential | None = None,
        accept: str | None = None,
    ) -> bytes:
        """`accept` overrides the JSON-first default for upstreams that frame XML correctly
        only when asked for it."""
        if credential is not None:
            credential.require_origin(url)
            conditional, max_redirects = False, 0
        try:
            async with asyncio.timeout(self._total_timeout_seconds):
                return await self._get_bytes(url, conditional, max_redirects, credential, accept)
        except TimeoutError as exc:
            if credential is not None:
                raise FeedFetchError("Authenticated feed request failed.") from None
            raise FeedTimeoutError("Feed request exceeded its total time limit.") from exc
        except (FeedFetchError, NotModified):
            if credential is not None:
                raise FeedFetchError("Authenticated feed request failed.") from None
            raise

    async def _get_bytes(
        self,
        url: str,
        conditional: bool,
        max_redirects: int,
        credential: FeedCredential | None,
        accept: str | None = None,
    ) -> bytes:
        if not 0 <= max_redirects <= MAX_REDIRECTS:
            raise ValueError("Invalid redirect budget")
        current = url
        for _ in range(max_redirects + 1):
            address = await assert_public_host(current)
            headers: dict[str, str] = {
                "Accept-Encoding": "identity",
                **({"Accept": accept} if accept else {}),
                **({credential.header_name: credential.authorization} if credential else {}),
            }
            validators = self._validators.get(url) if conditional else None
            if validators is not None:
                self._validators.move_to_end(url)
            if validators and validators.etag:
                headers["If-None-Match"] = validators.etag
            if validators and validators.last_modified:
                headers["If-Modified-Since"] = validators.last_modified
            target, extensions = self._pinned(current, address, headers)
            await self._pacer.wait(current)
            try:
                async with self._client.stream(
                    "GET", target, headers=headers, extensions=extensions, follow_redirects=False
                ) as response:
                    if response.status_code == 304:
                        raise NotModified(url)
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FeedFetchError("Redirect without a location")
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise await self._status_error(response, current)
                    body = await read_feed_response(
                        response,
                        self._max_bytes,
                        credentialed=credential is not None,
                        default_reader=self._read_bounded,
                    )
            except (httpx.HTTPError, BoundedGzipError) as exc:
                raise classify_fetch_error(exc) from None
            if conditional:
                self._record_validators(
                    url,
                    FeedValidators(
                        etag=response.headers.get("etag"),
                        last_modified=response.headers.get("last-modified"),
                    ),
                )
            return body
        raise FeedFetchError("Too many redirects")

    def _record_validators(self, url: str, validators: FeedValidators) -> None:
        """Inside a scheduler poll, validators only land once the whole poll is published."""
        scope = active_poll_scope()
        if scope is None:
            self._store_validators(url, validators)
        else:
            scope.stage((id(self), url), lambda: self._store_validators(url, validators))

    def _store_validators(self, url: str, validators: FeedValidators) -> None:
        self._validators[url] = validators
        self._validators.move_to_end(url)
        while len(self._validators) > MAX_VALIDATORS:
            self._validators.popitem(last=False)

    async def _status_error(self, response: httpx.Response, url: str) -> FeedFetchError:
        error = status_error(response.status_code, url, response.headers)
        if isinstance(error, FeedRateLimitedError):
            self._pacer.rate_limited(url, error.retry_after)
        return error

    async def get_json(
        self,
        url: str,
        *,
        conditional: bool = True,
        max_redirects: int = MAX_REDIRECTS,
        credential: FeedCredential | None = None,
    ) -> Any:
        try:
            return json.loads(
                await self.get_bytes(
                    url,
                    conditional=conditional,
                    max_redirects=max_redirects,
                    credential=credential,
                )
            )
        except (ValueError, RecursionError) as exc:
            if credential is not None:
                raise FeedFetchError("Authenticated feed returned invalid JSON.") from None
            raise FeedFetchError(f"Invalid JSON from {url}") from exc

    async def get_text(
        self,
        url: str,
        *,
        conditional: bool = True,
        max_redirects: int = MAX_REDIRECTS,
        credential: FeedCredential | None = None,
    ) -> str:
        return (
            await self.get_bytes(
                url,
                conditional=conditional,
                max_redirects=max_redirects,
                credential=credential,
            )
        ).decode("utf-8", "replace")

    @staticmethod
    def _pinned(
        url: str, address: str | None, headers: dict[str, str]
    ) -> tuple[str, dict[str, Any]]:
        """Connect to the checked address while presenting the original host name."""
        if address is None:
            return url, {}
        parts = urlsplit(url)
        host = parts.hostname or ""
        headers["Host"] = host if parts.port is None else f"{host}:{parts.port}"
        extensions: dict[str, Any] = {"sni_hostname": host} if parts.scheme == "https" else {}
        return pin_url(url, address), extensions

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        # HTTPX decodes compressed chunks before yielding them. Refuse that path so an
        # upstream cannot allocate a decompression bomb before our byte limit applies.
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        if encoding != "identity":
            raise FeedFetchError(
                f"Unsupported response content encoding: {safe_header_token(encoding)}"
            )
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

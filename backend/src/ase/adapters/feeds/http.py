"""Outbound HTTP for connectors: size caps, timeouts, conditional requests, no private hosts.

The SSRF guard resolves the hostname itself, checks every address, and then connects to
the address it checked (with the original host name in the Host header and the TLS
handshake), so a hostile DNS server cannot answer the check with a public address and
the connection with a private one.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from ase.adapters.feeds.secret_urls import SecretFeedUrl, protect_http_logs

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
MAX_VALIDATORS = 256


class FeedFetchError(Exception):
    """Any failure fetching a feed; the message is safe to show to an administrator."""


class FeedHttpStatusError(FeedFetchError):
    """HTTP status without exposing an untrusted response body."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} from {url}")
        self.status_code = status_code


class NotModified(Exception):
    """The upstream answered 304: nothing new since the last poll (an outcome, not a fault)."""


def _https_origin(url: str) -> tuple[str, int] | None:
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or any(ord(char) < 33 or ord(char) > 126 for char in url)
        ):
            return None
        port = parts.port if parts.port is not None else 443
        return (parts.hostname.lower(), port) if port > 0 else None
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class FeedCredential:
    """Request-local authorisation bound to one exact HTTPS origin, never shared headers."""

    origin: str
    authorization: str = field(repr=False)

    def __post_init__(self) -> None:
        try:
            parts = urlsplit(self.origin)
            valid = _https_origin(self.origin) is not None and not (
                parts.path or parts.query or parts.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("A credential requires an exact HTTPS origin without a path.")
        if (
            not self.authorization
            or len(self.authorization) > 8192
            or any(ord(char) < 32 or ord(char) > 126 for char in self.authorization)
        ):
            raise ValueError("Invalid request authorisation value.")

    def require_origin(self, url: str) -> None:
        if _https_origin(url) != _https_origin(self.origin):
            raise FeedFetchError("Request credential origin does not match the destination.")


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
        max_bytes: int = DEFAULT_MAX_BYTES,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if client is not None and (client.auth is not None or "authorization" in client.headers):
            raise ValueError("Shared feed clients must not carry global authorisation.")
        self._max_bytes = max_bytes
        self._validators: OrderedDict[str, _Validators] = OrderedDict()
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
    ) -> bytes:
        if credential is not None:
            credential.require_origin(url)
            conditional, max_redirects = False, 0
        try:
            return await self._get_bytes(url, conditional, max_redirects, credential)
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
    ) -> bytes:
        if not 0 <= max_redirects <= MAX_REDIRECTS:
            raise ValueError("Invalid redirect budget")
        current = url
        for _ in range(max_redirects + 1):
            address = await assert_public_host(current)
            headers: dict[str, str] = {
                "Accept-Encoding": "identity",
                **({"Authorization": credential.authorization} if credential else {}),
            }
            validators = self._validators.get(url) if conditional else None
            if validators is not None:
                self._validators.move_to_end(url)
            if validators and validators.etag:
                headers["If-None-Match"] = validators.etag
            if validators and validators.last_modified:
                headers["If-Modified-Since"] = validators.last_modified
            target, extensions = self._pinned(current, address, headers)
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
                    body = await self._read_bounded(response)
            except httpx.HTTPError as exc:
                raise FeedFetchError(f"{type(exc).__name__}: {exc}") from exc
            if conditional:
                self._validators[url] = _Validators(
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
                self._validators.move_to_end(url)
                while len(self._validators) > MAX_VALIDATORS:
                    self._validators.popitem(last=False)
            return body
        raise FeedFetchError("Too many redirects")

    async def _status_error(self, response: httpx.Response, url: str) -> FeedFetchError:
        return FeedHttpStatusError(response.status_code, url)

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
        if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
            raise FeedFetchError("Unsupported response content encoding")
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

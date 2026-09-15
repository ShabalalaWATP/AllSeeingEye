"""Public, DNS-pinned HTTPS transport for admitted original documents.

Each hop is independently checked against a reviewed source policy and an injected
rate/cooldown admission callback. The public-source DNS guard checks every answer;
only its selected checked address is recorded and used for the connection. HTTPX
never follows a redirect or decompresses content here. A fresh client has no shared
cookies, credentials, proxy environment or validator cache.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

import httpx

from ase.adapters.feeds.http import FeedFetchError, assert_public_host, pin_url
from ase.application.ports import Clock
from ase.application.research.original_policy import (
    MEDIA_EXTENSIONS,
    OriginalFetchRejected,
    OriginalFetchRequest,
    OriginalFetchResponse,
    OriginalTransportHop,
    public_address,
)

AdmitOriginalHop = Callable[[str, str], Awaitable[bool]]
_REDIRECTS = frozenset({301, 302, 303, 307, 308})


def _last_modified(header: str | None) -> datetime | None:
    if not header:
        return None
    try:
        value = parsedate_to_datetime(header)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    return value.astimezone(UTC) if value.utcoffset() is not None else None


def _bounded_headers(response: httpx.Response, request: OriginalFetchRequest) -> str:
    if response.headers.get("content-encoding", "identity").strip().lower() not in ("", "identity"):
        raise OriginalFetchRejected("compressed_response_not_permitted")
    declared = response.headers.get("content-length")
    if declared is not None and (not declared.isdecimal() or int(declared) > request.max_bytes):
        raise OriginalFetchRejected("body_limit_or_size_mismatch")
    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type not in request.accept:
        raise OriginalFetchRejected("unsupported_media_type")
    return str(media_type)


async def _bounded_body(response: httpx.Response, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_raw():
        total += len(chunk)
        if total > maximum:
            raise OriginalFetchRejected("body_limit_or_size_mismatch")
        chunks.append(chunk)
    if total == 0:
        raise OriginalFetchRejected("body_limit_or_size_mismatch")
    return b"".join(chunks)


class GuardedOriginalHttp:
    """Callable fetch adapter; composition must supply current source hop admission."""

    def __init__(
        self,
        user_agent: str,
        clock: Clock,
        admit_hop: AdmitOriginalHop,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if (
            not isinstance(user_agent, str)
            or not 1 <= len(user_agent) <= 160
            or any(ord(character) < 32 or ord(character) > 126 for character in user_agent)
        ):
            raise ValueError("Original transport requires a bounded user agent")
        self._user_agent = user_agent
        self._clock = clock
        self._admit_hop = admit_hop
        self._transport = transport

    async def fetch(self, request: OriginalFetchRequest) -> OriginalFetchResponse:
        """Return a receipt only after every requested byte and hop is validated."""
        policy = request.policy
        if (
            request.accept_encoding != "identity"
            or type(request.accept) is not tuple
            or not request.accept
            or len(request.accept) > len(MEDIA_EXTENSIONS)
            or any(
                type(media) is not str or media not in MEDIA_EXTENSIONS for media in request.accept
            )
            or len(set(request.accept)) != len(request.accept)
            or type(request.max_bytes) is not int
            or not 1 <= request.max_bytes <= policy.max_bytes
            or type(request.max_redirects) is not int
            or not 0 <= request.max_redirects <= policy.max_redirects
            or type(request.timeout_seconds) not in (int, float)
            or not 0 < request.timeout_seconds <= policy.timeout_seconds
            or not policy.permits(request.url, self._clock.now())
        ):
            raise OriginalFetchRejected("request_not_permitted")
        try:
            async with (
                asyncio.timeout(request.timeout_seconds),
                httpx.AsyncClient(
                    transport=self._transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx.Timeout(request.timeout_seconds),
                ) as client,
            ):
                return await self._follow(request, client)
        except TimeoutError:
            raise OriginalFetchRejected("fetch_timeout") from None
        except httpx.HTTPError:
            raise OriginalFetchRejected("transport_failed") from None

    async def _follow(  # noqa: PLR0912 - keep each hop's admission and receipt guards explicit
        self, request: OriginalFetchRequest, client: httpx.AsyncClient
    ) -> OriginalFetchResponse:
        current = request.url
        hops: list[OriginalTransportHop] = []
        for redirect_count in range(request.max_redirects + 1):
            if not request.policy.permits(current, self._clock.now()):
                raise OriginalFetchRejected("destination_not_permitted")
            try:
                admitted = await self._admit_hop(request.policy.source_id, current)
            except Exception:
                raise OriginalFetchRejected("source_admission_failed") from None
            if not admitted:
                raise OriginalFetchRejected("source_rate_or_terms_not_permitted")
            try:
                checked = await assert_public_host(current)
            except FeedFetchError:
                raise OriginalFetchRejected("destination_not_permitted") from None
            host = urlsplit(current).hostname or ""
            address = checked or host
            if not public_address(address):
                raise OriginalFetchRejected("destination_not_permitted")
            target, headers, extensions = self._pinned(current, checked, request)
            client.cookies.clear()
            async with client.stream(
                "GET",
                target,
                headers=headers,
                extensions=extensions,
                follow_redirects=False,
            ) as response:
                status = response.status_code
                if status in _REDIRECTS:
                    location = response.headers.get("location")
                    if (
                        redirect_count >= request.max_redirects
                        or not isinstance(location, str)
                        or not 1 <= len(location) <= 2048
                        or any(ord(char) < 33 or ord(char) > 126 for char in location)
                    ):
                        raise OriginalFetchRejected("redirect_limit")
                    next_url = urljoin(current, location)
                    if not request.policy.permits(next_url, self._clock.now()):
                        raise OriginalFetchRejected("destination_not_permitted")
                    hops.append(
                        OriginalTransportHop(current, (address,), address, status, location)
                    )
                    current = next_url
                    continue
                if status != 200:
                    raise OriginalFetchRejected("http_status_not_permitted")
                media_type = _bounded_headers(response, request)
                body = await _bounded_body(response, request.max_bytes)
                declared = response.headers.get("content-length")
                if declared is not None and int(declared) != len(body):
                    raise OriginalFetchRejected("body_limit_or_size_mismatch")
                if not request.policy.permits(current, self._clock.now()):
                    raise OriginalFetchRejected("destination_not_permitted")
                etag = response.headers.get("etag")
                if etag is not None and (len(etag) > 200 or any(ord(char) < 32 for char in etag)):
                    raise OriginalFetchRejected("transport_receipt_invalid")
                hops.append(OriginalTransportHop(current, (address,), address, status))
                return OriginalFetchResponse(
                    requested_url=request.url,
                    canonical_url=current,
                    hops=tuple(hops),
                    media_type=media_type,
                    body=body,
                    wire_body_bytes=len(body),
                    last_modified_at=_last_modified(response.headers.get("last-modified")),
                    etag=etag,
                )
        raise OriginalFetchRejected("redirect_limit")

    def _pinned(
        self, url: str, address: str | None, request: OriginalFetchRequest
    ) -> tuple[str, dict[str, str], dict[str, str]]:
        host = urlsplit(url).hostname or ""
        headers = {
            "User-Agent": self._user_agent,
            "Accept": ", ".join(request.accept),
            "Accept-Encoding": "identity",
        }
        if address is None:
            return url, headers, {}
        host_header = f"[{host}]" if ":" in host else host
        headers["Host"] = host_header
        return pin_url(url, address), headers, {"sni_hostname": host}

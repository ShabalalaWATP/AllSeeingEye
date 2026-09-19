"""Wayback Machine archiver: reuse a snapshot taken since publication, else ask for a new one.

The Availability API is asked first (docs/02, Internet Archive rows); only when it has
nothing recent enough is the anonymous Save Page Now endpoint used, which is rate limited
and refuses many domains. A failure means "no archive" for that item; nothing retries.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

import httpx
import structlog

AVAILABILITY_URL = "https://archive.org/wayback/available"
SAVE_URL = "https://web.archive.org/save/"
SNAPSHOT_PREFIXES = ("http://web.archive.org/web/", "https://web.archive.org/web/")
DEFAULT_PAUSE_SECONDS = 4.0
MAX_URL_LENGTH = 2_000
MAX_AVAILABILITY_BYTES = 256 * 1024
MAX_REDIRECTS = 3
ALLOWED_ARCHIVE_HOSTS = frozenset({"archive.org", "web.archive.org"})

log = structlog.get_logger(__name__)


def _acceptable(url: str) -> bool:
    return url.lower().startswith(("http://", "https://")) and len(url) <= MAX_URL_LENGTH


def _https(snapshot: str) -> str:
    return snapshot.replace("http://web.archive.org/", "https://web.archive.org/", 1)


class NullArchiver:
    """Archiving switched off: every item stays unarchived."""

    async def archive(self, url: str, published_at: datetime) -> str | None:
        return None

    async def aclose(self) -> None:
        return None


class WaybackArchiver:
    def __init__(
        self,
        user_agent: str,
        *,
        pause_seconds: float = DEFAULT_PAUSE_SECONDS,
        timeout_seconds: float = 45.0,
        client: httpx.AsyncClient | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds), follow_redirects=False
        )
        self._client.headers["User-Agent"] = user_agent
        self._pause = pause_seconds
        self._timeout = timeout_seconds
        self._sleep = sleeper

    async def aclose(self) -> None:
        await self._client.aclose()

    async def archive(self, url: str, published_at: datetime) -> str | None:
        if not _acceptable(url):
            return None
        existing = await self._available(url, since=published_at)
        if existing:
            return existing
        await self._sleep(self._pause)
        return await self._save(url)

    async def _available(self, url: str, *, since: datetime | None) -> str | None:
        try:
            target = httpx.URL(AVAILABILITY_URL, params={"url": url})
            async with asyncio.timeout(self._timeout):
                for _hop in range(MAX_REDIRECTS + 1):
                    async with self._client.stream(
                        "GET",
                        target,
                        headers={"Accept-Encoding": "identity"},
                        follow_redirects=False,
                    ) as response:
                        if response.is_redirect:
                            target = _redirect_target(target, response)
                            continue
                        response.raise_for_status()
                        data = json.loads(await _bounded_body(response))
                        break
                else:
                    raise ValueError("too many redirects")
        except (TimeoutError, httpx.HTTPError, ValueError, RecursionError) as exc:
            log.debug("archive.availability_failed", error=type(exc).__name__)
            return None
        closest = (
            data.get("archived_snapshots", {}).get("closest") if isinstance(data, dict) else None
        )
        if not isinstance(closest, dict) or not closest.get("available"):
            return None
        snapshot = str(closest.get("url", ""))
        if not snapshot.startswith(SNAPSHOT_PREFIXES):
            return None
        if since is not None:
            try:
                taken = datetime.strptime(str(closest.get("timestamp", "")), "%Y%m%d%H%M%S")
            except ValueError:
                return None
            if taken.replace(tzinfo=UTC) < since:
                return None
        return _https(snapshot)

    async def _save(self, url: str) -> str | None:
        try:
            target = httpx.URL(SAVE_URL + url)
            async with asyncio.timeout(self._timeout):
                for _hop in range(MAX_REDIRECTS + 1):
                    async with self._client.stream(
                        "GET", target, follow_redirects=False
                    ) as response:
                        if response.is_redirect:
                            target = _redirect_target(target, response)
                            continue
                        if response.status_code != 200:
                            log.debug("archive.save_refused", status=response.status_code)
                            return None
                        location = str(response.headers.get("content-location", ""))
                        final = str(response.url)
                        break
                else:
                    return None
        except (TimeoutError, httpx.HTTPError, ValueError) as exc:
            log.debug("archive.save_failed", error=type(exc).__name__)
            return None
        if location.startswith("/web/"):
            return "https://web.archive.org" + location
        if final.startswith(SNAPSHOT_PREFIXES):
            return _https(final)
        return None


def _redirect_target(current: httpx.URL, response: httpx.Response) -> httpx.URL:
    location = response.headers.get("location")
    if not location:
        raise ValueError("redirect without location")
    target = httpx.URL(urljoin(str(current), location))
    parsed = urlsplit(str(target))
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_ARCHIVE_HOSTS
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("unsafe archive redirect")
    return target


async def _bounded_body(response: httpx.Response) -> bytes:
    encoding = response.headers.get("content-encoding", "identity").casefold()
    if encoding not in ("", "identity"):
        raise ValueError("compressed archive response")
    raw_length = response.headers.get("content-length")
    if raw_length is not None:
        try:
            if int(raw_length) > MAX_AVAILABILITY_BYTES:
                raise ValueError("archive response too large")
        except ValueError:
            raise ValueError("invalid archive content length") from None
    body = bytearray()
    if response.is_stream_consumed:
        body.extend(response.content)
    else:
        async for chunk in response.aiter_raw():
            body.extend(chunk)
            if len(body) > MAX_AVAILABILITY_BYTES:
                raise ValueError("archive response too large")
    if len(body) > MAX_AVAILABILITY_BYTES:
        raise ValueError("archive response too large")
    return bytes(body)

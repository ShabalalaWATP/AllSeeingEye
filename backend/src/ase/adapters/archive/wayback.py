"""Wayback Machine archiver: reuse a snapshot taken since publication, else ask for a new one.

The Availability API is asked first (docs/02, Internet Archive rows); only when it has
nothing recent enough is the anonymous Save Page Now endpoint used, which is rate limited
and refuses many domains. A failure means "no archive" for that item; nothing retries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx
import structlog

AVAILABILITY_URL = "https://archive.org/wayback/available"
SAVE_URL = "https://web.archive.org/save/"
SNAPSHOT_PREFIXES = ("http://web.archive.org/web/", "https://web.archive.org/web/")
DEFAULT_PAUSE_SECONDS = 4.0
MAX_URL_LENGTH = 2_000

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
            timeout=httpx.Timeout(timeout_seconds), follow_redirects=True
        )
        self._client.headers["User-Agent"] = user_agent
        self._pause = pause_seconds
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
            response = await self._client.get(AVAILABILITY_URL, params={"url": url})
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
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
            async with self._client.stream("GET", SAVE_URL + url) as response:
                if response.status_code != 200:
                    log.debug("archive.save_refused", status=response.status_code)
                    return None
                location = str(response.headers.get("content-location", ""))
                final = str(response.url)
        except httpx.HTTPError as exc:
            log.debug("archive.save_failed", error=type(exc).__name__)
            return None
        if location.startswith("/web/"):
            return "https://web.archive.org" + location
        if final.startswith(SNAPSHOT_PREFIXES):
            return _https(final)
        return None

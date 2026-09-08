"""CelesTrak GP retrieval with restart-safe request limits and warm-cache recovery."""

from __future__ import annotations

import asyncio
import contextlib
import csv
import io
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from itertools import islice
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, FeedHttpStatusError, NotModified
from ase.adapters.feeds.satellite_cache import (
    ELEMENT_TTL,
    MAX_OBJECTS,
    ElementState,
    SatelliteCache,
    bounded_rows,
)
from ase.adapters.feeds.satellite_http import ElementsNotUpdated
from ase.application.ports.feed_diagnostics import FeedDeferred
from ase.domain.sources import SourceSpec


class SatelliteDeferred(FeedDeferred, FeedFetchError):
    """Retains feed-fetch compatibility while avoiding repeated scheduler failure counts."""


def parse_csv(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames or "NORAD_CAT_ID" not in reader.fieldnames:
        raise ValueError("Satellite catalogue is missing orbital fields")
    return list(islice(reader, MAX_OBJECTS))


class SatelliteElements:
    def __init__(
        self,
        http: FeedHttpClient,
        spec: SourceSpec,
        cache_dir: Path | None,
        validate: Callable[[list[dict[str, Any]], datetime], bool],
    ) -> None:
        self.http, self.spec = http, spec
        self.cache = SatelliteCache(cache_dir, spec.id, spec.url) if cache_dir else None
        self.state = ElementState()
        self.loaded = False
        self.retry_requested = False
        self.validate = validate

    async def _save(self) -> None:
        if self.cache:
            # Rows are replaced, never edited. A snapshot prevents later metadata changes
            # leaking into this write; keep the connector lock until the thread finishes.
            write = asyncio.create_task(asyncio.to_thread(self.cache.save, replace(self.state)))
            try:
                await asyncio.shield(write)
            except asyncio.CancelledError:
                while not write.done():
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await asyncio.shield(write)
                with contextlib.suppress(Exception):
                    write.result()
                raise

    async def _load(self, now: datetime) -> None:
        if not self.loaded:
            if self.cache:
                self.state = await asyncio.to_thread(self.cache.load, now)
            self.loaded = True
        state = self.state
        if self.retry_requested:
            state.blocked = False
            self.retry_requested = False
            await self._save()

    async def refresh(self, now: datetime) -> None:
        await self._load(now)
        state = self.state
        if state.blocked or (state.retry_at is not None and now < state.retry_at):
            return
        if state.fetched_at is not None and now - state.fetched_at < ELEMENT_TTL:
            return
        # Reserve before I/O: cancellation or a backend restart cannot reset the limit.
        state.retry_at = now + ELEMENT_TTL
        state.error = "CelesTrak download incomplete; waiting two hours before retrying"
        try:
            await self._save()
        except OSError:
            state.error = (
                "CelesTrak cache is not writable; download paused to protect request limits"
            )
            return
        try:
            format_name = parse_qs(urlsplit(self.spec.url).query).get("FORMAT", ["CSV"])[0].upper()
            if format_name == "CSV":
                text = await self.http.get_text(self.spec.url, conditional=False)
                data = await asyncio.to_thread(parse_csv, text)
            else:
                data = await self.http.get_json(self.spec.url, conditional=False)
            rows = await asyncio.to_thread(bounded_rows, data)
            if state.rows and not await asyncio.to_thread(self.validate, rows, now):
                raise ValueError("Replacement catalogue has no usable orbital elements")
        except (NotModified, ElementsNotUpdated):
            if not state.rows:
                state.error = (
                    "CelesTrak returned unchanged data but no local elements are available"
                )
            else:
                state.error = None
        except (FeedFetchError, ValueError, csv.Error) as exc:
            state.blocked = isinstance(exc, FeedHttpStatusError) and exc.status_code in (403, 404)
            state.error = (
                (
                    f"CelesTrak HTTP {exc.status_code}; downloads paused. "
                    "Review the provider and retry this source."
                )
                if state.blocked and isinstance(exc, FeedHttpStatusError)
                else (
                    f"CelesTrak retrieval failed ({str(exc)[:150]}); "
                    "waiting two hours before retrying"
                )
            )
        else:
            state.rows, state.fetched_at, state.error = rows, now, None
        try:
            await self._save()
        except OSError:
            state.error = "CelesTrak elements are in memory but the cache could not be saved"

    def require_available(self, now: datetime) -> None:
        if not self.state.rows:
            raise SatelliteDeferred(
                self.state.error or "No usable CelesTrak elements are available",
                max(self.state.retry_at or now, now + self.spec.poll_interval),
            )

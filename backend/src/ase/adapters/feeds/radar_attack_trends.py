"""Bounded Cloudflare Radar attack distributions, kept separate from incidents."""

from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal

from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import Category, Reliability
from ase.domain.research_scope import COUNTRY_CODES
from ase.domain.sources import SourceKind, SourceSpec

SPEC = SourceSpec(
    id="cloudflare_radar_attack_trends",
    name="Cloudflare Radar attack distributions",
    organisation="Cloudflare Radar",
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://api.cloudflare.com/client/v4/radar/attacks/layer7/top/locations/target",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=30),
    licence_note="CC BY-NC 4.0; non-commercial use only, attribute Cloudflare Radar",
    homepage="https://radar.cloudflare.com/security/application-layer",
    requires_key=True,
    instrument=True,
)

Layer = Literal["layer3", "layer7"]
Status = Literal["ready", "partial", "stale", "unavailable", "not_configured", "disabled"]
_ISO = re.compile(r"[A-Z]{2}")
_CACHE = timedelta(minutes=30)
_RETRY = timedelta(minutes=5)
_MAX_STALE = timedelta(hours=2)


@dataclass(frozen=True, slots=True)
class RadarAttackCountry:
    country_iso: str
    country_name: str
    rank: int
    share_percent: float


@dataclass(frozen=True, slots=True)
class RadarAttackUnit:
    name: Literal["*"]
    value: Literal["bytes", "requests"]


@dataclass(frozen=True, slots=True)
class RadarAttackLayer:
    layer: Layer
    period_from: datetime
    period_to: datetime
    updated_at: datetime | None
    unit: Literal["bytes", "requests"]
    countries: tuple[RadarAttackCountry, ...]
    provider_units: tuple[RadarAttackUnit, ...] = ()
    provider_version: str | None = None


@dataclass(frozen=True, slots=True)
class RadarAttackSnapshot:
    status: Status
    fetched_at: datetime | None
    layers: tuple[RadarAttackLayer, ...]
    source_url: str = SPEC.homepage


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _country(row: object) -> RadarAttackCountry | None:
    if not isinstance(row, dict):
        return None
    iso, name, rank = (
        row.get("targetCountryAlpha2"),
        row.get("targetCountryName"),
        row.get("rank"),
    )
    if (
        not isinstance(iso, str)
        or not _ISO.fullmatch(iso)
        or iso not in COUNTRY_CODES
        or not isinstance(name, str)
        or not name.strip()
        or not isinstance(rank, int)
        or isinstance(rank, bool)
        or not 1 <= rank <= 10
    ):
        return None
    raw_value = row.get("value")
    if not isinstance(raw_value, str | int | float) or isinstance(raw_value, bool):
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return RadarAttackCountry(iso, " ".join(name.split())[:80], rank, value)


def _units(meta: dict[str, object], layer: Layer) -> tuple[RadarAttackUnit, ...]:
    """Retain the provider unit, never infer bytes merely from the layer name.

    Cloudflare's target-location API reference declares units as name/value objects;
    its layer-3 example returns requests. Other units require an explicit reviewed contract.
    """
    units = meta.get("units")
    if not isinstance(units, list) or len(units) != 1 or not isinstance(units[0], dict):
        raise FeedFetchError("Cloudflare Radar unit metadata is missing or malformed")
    name, value = units[0].get("name"), units[0].get("value")
    if (
        name != "*"
        or value not in ("bytes", "requests")
        or (layer == "layer7" and value != "requests")
    ):
        raise FeedFetchError("Cloudflare Radar unit metadata is unsupported")
    return (RadarAttackUnit("*", value),)


class RadarAttackTrends:
    """One cached provider read for all users; no per-user Radar request fan-out."""

    def __init__(self, http: FeedHttpClient, clock: Clock, token: str | None) -> None:
        self._http, self._clock = http, clock
        self._credential = (
            FeedCredential(origin="https://api.cloudflare.com", authorization=f"Bearer {token}")
            if token
            else None
        )
        self._lock = asyncio.Lock()
        self._next_refresh: datetime | None = None
        self._snapshot: RadarAttackSnapshot | None = None
        self._layer_snapshots: dict[Layer, RadarAttackSnapshot] = {}
        self._layer_refresh: dict[Layer, datetime] = {}

    async def read_layer(self, layer: Layer) -> RadarAttackSnapshot:
        """At most one fixed endpoint request, sharing the dashboard's per-layer cache."""
        if layer not in ("layer3", "layer7"):
            raise ValueError("Unsupported Radar layer")
        if self._credential is None:
            return RadarAttackSnapshot("not_configured", None, ())
        async with self._lock:
            return await self._layer(layer, self._clock.now())

    async def _layer(self, layer: Layer, now: datetime) -> RadarAttackSnapshot:
        cached = self._layer_snapshots.get(layer)
        if cached is not None and now < self._layer_refresh[layer]:
            return cached
        result = await self._read_one(layer)
        if result is not None:
            snapshot = RadarAttackSnapshot("ready", self._clock.now(), (result,))
            refresh = _CACHE
        else:
            fresh = (
                cached is not None
                and cached.fetched_at is not None
                and now - cached.fetched_at <= _MAX_STALE
            )
            snapshot = (
                replace(cached, status="stale")
                if fresh and cached
                else RadarAttackSnapshot("unavailable", None, ())
            )
            refresh = _RETRY
        self._layer_snapshots[layer], self._layer_refresh[layer] = snapshot, now + refresh
        return snapshot

    async def read(self) -> RadarAttackSnapshot:
        if self._credential is None:
            return RadarAttackSnapshot("not_configured", None, ())
        now = self._clock.now()
        if self._next_refresh and now < self._next_refresh and self._snapshot:
            return self._snapshot
        async with self._lock:
            now = self._clock.now()
            if self._next_refresh and now < self._next_refresh and self._snapshot:
                return self._snapshot
            readings = await asyncio.gather(self._layer("layer3", now), self._layer("layer7", now))
            successful = tuple(
                layer
                for reading in readings
                if reading.status == "ready"
                for layer in reading.layers
            )
            if successful:
                status: Status = "ready" if len(successful) == 2 else "partial"
                fetched = min(
                    reading.fetched_at
                    for reading in readings
                    if reading.status == "ready" and reading.fetched_at is not None
                )
                self._snapshot = RadarAttackSnapshot(status, fetched, successful)
                self._next_refresh = now + (_CACHE if status == "ready" else _RETRY)
            else:
                fresh = (
                    self._snapshot is not None
                    and self._snapshot.fetched_at is not None
                    and now - self._snapshot.fetched_at <= _MAX_STALE
                )
                self._snapshot = (
                    replace(self._snapshot, status="stale")
                    if fresh and self._snapshot
                    else RadarAttackSnapshot("unavailable", None, ())
                )
                self._next_refresh = now + _RETRY
            return self._snapshot

    async def _read_one(self, layer: Layer) -> RadarAttackLayer | None:
        try:
            async with asyncio.timeout(12):
                return await self._fetch(layer)
        except (FeedFetchError, TimeoutError, OSError, ValueError):
            return None

    async def _fetch(self, layer: Layer) -> RadarAttackLayer:
        credential = self._credential
        if credential is None:
            raise FeedFetchError("Cloudflare Radar token is not configured")
        url = (
            f"https://api.cloudflare.com/client/v4/radar/attacks/{layer}"
            "/top/locations/target?dateRange=1d&limit=10&format=json"
        )
        data = await self._http.get_json(
            url, credential=credential, conditional=False, max_redirects=0
        )
        if not isinstance(data, dict) or data.get("success") is not True:
            raise FeedFetchError("Cloudflare Radar attack distribution failed")
        result = data.get("result")
        if not isinstance(result, dict):
            raise FeedFetchError("Cloudflare Radar attack distribution is missing")
        meta, rows = result.get("meta"), result.get("top_0")
        if not isinstance(meta, dict) or not isinstance(rows, list) or not 1 <= len(rows) <= 10:
            raise FeedFetchError("Cloudflare Radar attack distribution is malformed")
        ranges = meta.get("dateRange")
        interval = ranges[0] if isinstance(ranges, list) and len(ranges) == 1 else None
        if not isinstance(interval, dict) or meta.get("normalization") != "PERCENTAGE":
            raise FeedFetchError("Cloudflare Radar attack distribution has unexpected units")
        start, end = _date(interval.get("startTime")), _date(interval.get("endTime"))
        if start is None or end is None or not timedelta(0) < end - start <= timedelta(days=1):
            raise FeedFetchError("Cloudflare Radar attack distribution has no valid period")
        updated = _date(meta.get("lastUpdated"))
        if updated is None:
            raise FeedFetchError("Cloudflare Radar dataset update time is missing or invalid")
        units = _units(meta, layer)
        version = meta.get("version")
        if version is not None and (
            not isinstance(version, str)
            or not 1 <= len(version) <= 100
            or any(ord(char) < 32 for char in version)
        ):
            raise FeedFetchError("Cloudflare Radar dataset version is malformed")
        countries = [country for row in rows if (country := _country(row)) is not None]
        if (
            len(countries) != len(rows)
            or len({row.country_iso for row in countries}) != len(rows)
            or {row.rank for row in countries} != set(range(1, len(rows) + 1))
            or math.fsum(row.share_percent for row in countries) > 100.0001
        ):
            raise FeedFetchError("Cloudflare Radar attack distribution has no usable countries")
        countries.sort(key=lambda row: row.rank)
        return RadarAttackLayer(
            layer,
            start,
            end,
            updated,
            units[0].value,
            tuple(countries),
            units,
            version,
        )

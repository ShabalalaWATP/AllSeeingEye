"""Frontline geometry and spotted losses from fixed providers, behind operator flags.

DeepStateMap's API is used only when the operator records granted access; OCHA's line only for
a humanitarian deployment; WarSpotting only after its terms are read. Each provider is one
bounded request on a cooldown, keeping its last good snapshot and reporting stale or
unavailable states rather than substituting another source.
"""

from __future__ import annotations

import asyncio
import math
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from ase.adapters.feeds.conflict_values import text
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.ukraine.frontline import (
    MAX_FRONTLINE_FEATURES,
    MAX_SPOTTED,
    FrontlineFeature,
    FrontlineKind,
    FrontlineSnapshot,
    FrontlineState,
    FrontlineStatus,
    SpottedLoss,
    SpottedState,
)

DEEPSTATE_URL = "https://deepstatemap.live/api/history/last"
OCHA_URL = (
    "https://gis.unocha.org/server/rest/services/Hosted/UKR_Front_Line/FeatureServer/0/query"
    "?where=1%3D1&outFields=date,source&f=geojson"
)
WARSPOTTING_URL = "https://ukr.warspotting.net/api/losses/russia/{month}"
DEEPSTATE_COOLDOWN = timedelta(hours=6)
OCHA_COOLDOWN = timedelta(days=7)
SPOTTED_COOLDOWN = timedelta(hours=6)
FAILURE_RETRY = timedelta(minutes=5)
PAYLOAD_ERRORS = (FeedFetchError, NotModified, ValueError, KeyError, TypeError, AttributeError)
DEEPSTATE_TERMS = (
    "DeepStateMap licence of 3 September 2025: API use by the rights holder's permission; "
    "shown with the DeepStateMap credit and link, never redistributed."
)
OCHA_TERMS = "UN OCHA hosted layer, intended for humanitarian purposes; credit ISW and CTP."
SPOTTED_TERMS = "WarSpotting, geolocated visually confirmed Russian losses; terms per its site."
_KINDS = {
    "geoJSON.status.occupied": FrontlineKind.OCCUPIED,
    "geoJSON.status.dismissed": FrontlineKind.LIBERATED,
    "geoJSON.status.unknown": FrontlineKind.UNKNOWN,
}


Path = tuple[tuple[float, float], ...]
Rings = tuple[Path, ...]


def _number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _path(positions: Any) -> Path | None:
    """GeoJSON positions may carry altitude; each needs at least two finite numbers."""
    if not isinstance(positions, list):
        return None
    parsed: list[tuple[float, float]] = []
    for position in positions:
        if not isinstance(position, list) or len(position) < 2:
            return None
        x, y, *_ = position
        if not (_number(x) and _number(y)):
            return None
        parsed.append((round(float(x), 4), round(float(y), 4)))
    return tuple(parsed)


def _paths(coordinates: Any) -> Rings | None:
    """Every member must be a valid path, or the whole geometry is skipped."""
    if not isinstance(coordinates, list):
        return None
    paths: list[Path] = []
    for member in coordinates:
        path = _path(member)
        if path is None:
            return None
        paths.append(path)
    return tuple(paths)


def _polygons(geometry: dict[str, Any]) -> tuple[Rings, ...] | None:
    coordinates = geometry.get("coordinates")
    if geometry.get("type") == "Polygon":
        rings = _paths(coordinates)
        return None if rings is None else (rings,)
    if not isinstance(coordinates, list):
        return None
    polygons: list[Rings] = []
    for polygon in coordinates:
        rings = _paths(polygon)
        if rings is None:
            return None
        polygons.append(rings)
    return tuple(polygons)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_deepstate(payload: Any) -> tuple[str | None, tuple[FrontlineFeature, ...]]:
    """Polygons classed by DeepState's own status names; unit markers and arrows are dropped."""
    collection = payload.get("map") if isinstance(payload, dict) else None
    features = collection.get("features") if isinstance(collection, dict) else None
    if not isinstance(features, list):
        raise FeedFetchError("DeepState returned an invalid map.")
    parsed: list[FrontlineFeature] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = _mapping(feature.get("geometry"))
        name = text(_mapping(feature.get("properties")).get("name"), 300)
        kind = next((k for key, k in _KINDS.items() if key in name), None)
        if kind is None and "geoJSON.territories." in name:
            kind = FrontlineKind.HISTORICAL
        if kind is None or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        polygons = _polygons(geometry)
        if polygons is None:
            continue
        parts = re.split(r"\s*///\s*", name)
        label = parts[1] if len(parts) > 1 else parts[0]
        parsed.append(FrontlineFeature(kind=kind, label=label.strip()[:120], polygons=polygons))
    if len(parsed) > MAX_FRONTLINE_FEATURES:
        raise FeedFetchError("DeepState returned more areas than the bound.")
    return text(payload.get("datetime"), 40) or None, tuple(parsed)


def parse_ocha(payload: Any) -> tuple[str | None, tuple[FrontlineFeature, ...]]:
    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list):
        raise FeedFetchError("OCHA returned an invalid layer.")
    lines: list[Path] = []
    newest = 0
    for feature in features[:MAX_FRONTLINE_FEATURES]:
        if not isinstance(feature, dict):
            continue
        geometry = _mapping(feature.get("geometry"))
        stamp = _mapping(feature.get("properties")).get("date")
        if isinstance(stamp, int | float) and _number(stamp):
            newest = max(newest, int(stamp))
        if geometry.get("type") == "LineString":
            line = _path(geometry.get("coordinates"))
            lines.extend(() if line is None else (line,))
        elif geometry.get("type") == "MultiLineString":
            lines.extend(_paths(geometry.get("coordinates")) or ())
    assessed = datetime.fromtimestamp(newest / 1000, tz=UTC).date().isoformat() if newest else None
    feature = FrontlineFeature(kind=FrontlineKind.LINE, label="Front line", lines=tuple(lines))
    return assessed, (feature,) if lines else ()


def parse_spotted(payload: Any) -> list[SpottedLoss]:
    losses = payload.get("losses") if isinstance(payload, dict) else None
    if not isinstance(losses, list):
        raise FeedFetchError("WarSpotting returned an invalid list.")
    parsed: list[SpottedLoss] = []
    for row in losses:
        geo = text(row.get("geo"), 60).split(",") if isinstance(row, dict) else []
        if len(geo) != 2:
            continue
        try:
            lat, lon = float(geo[0]), float(geo[1])
            on = date.fromisoformat(text(row.get("date"), 10))
        except ValueError:
            continue
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            continue
        parsed.append(
            SpottedLoss(
                id=int(row.get("id") or 0),
                lat=lat,
                lon=lon,
                model=text(row.get("model"), 80),
                equipment_type=text(row.get("type"), 60),
                status=text(row.get("status"), 30),
                lost_by=text(row.get("lost_by"), 20),
                on=on,
                place=text(row.get("nearest_location"), 120),
            )
        )
    return parsed[:MAX_SPOTTED]


class FrontlineProviders:
    """Chooses one provider from the operator's flags and serves its cached snapshot."""

    def __init__(
        self, http: FeedHttpClient, clock: Clock, *, deepstate: bool, ocha: bool, spotted: bool
    ) -> None:
        self._http, self._clock = http, clock
        self._deepstate, self._ocha, self._spotted = deepstate, ocha, spotted
        self._lock = asyncio.Lock()
        self._frontline: FrontlineState | None = None
        self._frontline_due: datetime | None = None
        self._spotted_state: SpottedState | None = None
        self._spotted_due: datetime | None = None

    async def snapshot(self) -> FrontlineState:
        if not self._deepstate and not self._ocha:
            return FrontlineState(
                FrontlineStatus.DISABLED,
                "No frontline provider is enabled. DeepStateMap needs the rights holder's "
                "permission and OCHA's layer is for humanitarian deployments; see the operator "
                "flags.",
            )
        cooldown = DEEPSTATE_COOLDOWN if self._deepstate else OCHA_COOLDOWN
        async with self._lock:
            now = self._clock.now()
            if self._frontline and self._frontline_due and now < self._frontline_due:
                return self._frontline
            self._frontline = await self._fetch_frontline(now)
            self._frontline_due = _next_refresh(self._frontline.status, now, cooldown)
            return self._frontline

    async def _fetch_frontline(self, now: datetime) -> FrontlineState:
        provider, url, terms, attribution, parse = (
            ("deepstate", DEEPSTATE_URL, DEEPSTATE_TERMS, "DeepStateMap.live", parse_deepstate)
            if self._deepstate
            else ("ocha", OCHA_URL, OCHA_TERMS, "UN OCHA, ISW and AEI's CTP", parse_ocha)
        )
        previous = self._frontline.snapshot if self._frontline else None
        try:
            assessed, features = parse(await self._http.get_json(url, conditional=False))
            snapshot = FrontlineSnapshot(provider, attribution, terms, assessed, now, features)
        except PAYLOAD_ERRORS as exc:
            if previous is not None:
                return FrontlineState(
                    FrontlineStatus.STALE, f"Refresh failed: {_reason(exc)}", previous
                )
            return FrontlineState(
                FrontlineStatus.UNAVAILABLE, f"Provider unavailable: {_reason(exc)}"
            )
        return FrontlineState(FrontlineStatus.READY, "Provider snapshot", snapshot)

    async def spotted(self) -> SpottedState:
        if not self._spotted:
            return SpottedState(
                FrontlineStatus.DISABLED,
                "WarSpotting layer is off until the operator has read its terms.",
                SPOTTED_TERMS,
                None,
            )
        async with self._lock:
            now = self._clock.now()
            if self._spotted_state and self._spotted_due and now < self._spotted_due:
                return self._spotted_state
            self._spotted_state = await self._fetch_spotted(now)
            self._spotted_due = _next_refresh(self._spotted_state.status, now, SPOTTED_COOLDOWN)
            return self._spotted_state

    async def _fetch_spotted(self, now: datetime) -> SpottedState:
        previous = self._spotted_state
        losses: list[SpottedLoss] = []
        try:
            for month in _recent_months(now.date()):
                payload = await self._http.get_json(
                    WARSPOTTING_URL.format(month=month), conditional=False
                )
                losses.extend(parse_spotted(payload))
        except PAYLOAD_ERRORS as exc:
            if previous is not None and previous.losses:
                return SpottedState(
                    FrontlineStatus.STALE,
                    f"Refresh failed: {_reason(exc)}",
                    SPOTTED_TERMS,
                    previous.downloaded_at,
                    previous.losses,
                )
            return SpottedState(
                FrontlineStatus.UNAVAILABLE,
                f"Provider unavailable: {_reason(exc)}",
                SPOTTED_TERMS,
                None,
            )
        losses.sort(key=lambda loss: loss.on, reverse=True)
        return SpottedState(
            FrontlineStatus.READY,
            "Provider snapshot",
            SPOTTED_TERMS,
            now,
            tuple(losses[:MAX_SPOTTED]),
        )


def _next_refresh(status: FrontlineStatus, now: datetime, cooldown: timedelta) -> datetime:
    """The long provider cooldown follows a good snapshot only; failures retry sooner."""
    return now + (cooldown if status is FrontlineStatus.READY else FAILURE_RETRY)


def _reason(exc: Exception) -> str:
    """Upstream fetch errors are already bounded; parser internals are not shown."""
    if isinstance(exc, FeedFetchError | NotModified):
        return str(exc)
    return "the provider returned a malformed payload."


def _recent_months(today: date) -> tuple[str, str]:
    first = today.replace(day=1)
    previous = (first - timedelta(days=1)).replace(day=1)
    return (previous.strftime("%Y-%m"), first.strftime("%Y-%m"))

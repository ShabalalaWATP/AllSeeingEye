"""NASA EONET: curated natural events (storms, fires, volcanoes, ice) with source links."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Point,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

SPEC = SourceSpec(
    id="nasa_eonet",
    name="NASA EONET natural events",
    organisation="NASA Earth Observatory",
    category=Category.DISASTER,
    kind=SourceKind.API,
    url="https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=10),
    licence_note="NASA open data",
    homepage="https://eonet.gsfc.nasa.gov/docs/v3",
    instrument=True,
)

_CAMEL = re.compile(r"(?<!^)(?=[A-Z])")
ACRES_FOR_FULL_SEVERITY = 100_000.0


def _snake(value: str) -> str:
    return _CAMEL.sub("_", value).lower()


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _centre(geometry: dict[str, Any]) -> Point | None:
    coords = geometry.get("coordinates")
    try:
        if geometry.get("type") == "Point" and isinstance(coords, list):
            return Point(lon=float(coords[0]), lat=float(coords[1]))
        if geometry.get("type") == "Polygon" and isinstance(coords, list) and coords:
            ring = [(float(c[0]), float(c[1])) for c in coords[0]]
            return Point(
                lon=sum(c[0] for c in ring) / len(ring), lat=sum(c[1] for c in ring) / len(ring)
            )
    except (TypeError, ValueError, IndexError, ZeroDivisionError):
        return None
    return None


class EonetConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        items = data.get("events", []) if isinstance(data, dict) else []
        return [event for item in items if (event := self._to_event(item, now))]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        upstream_id = item.get("id")
        geometries = item.get("geometry") or []
        if not upstream_id or not geometries:
            return None
        latest = geometries[-1]
        point = _centre(latest)
        if point is None:
            return None
        categories = item.get("categories") or [{}]
        category_id = str(categories[0].get("id") or "event")
        category_title = str(categories[0].get("title") or category_id)
        sources = item.get("sources") or []
        url = (sources[0].get("url") if sources else None) or item.get("link")
        magnitude = latest.get("magnitudeValue")
        unit = latest.get("magnitudeUnit")
        severity = None
        if isinstance(magnitude, int | float) and unit == "acres":
            severity = min(1.0, float(magnitude) / ACRES_FOR_FULL_SEVERITY)
        published = _parse_date(latest.get("date")) or now
        summary = item.get("description") or f"{category_title} tracked by NASA EONET."
        return Event(
            id=event_id(self.spec.id, str(upstream_id)),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype=_snake(category_id),
            title=str(item.get("title") or category_title),
            summary=summary,
            url=url,
            published_at=published,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({_snake(category_id)}),
            severity=severity,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Curated by NASA EONET from named upstream sources",
            attributes=freeze_attributes(
                {
                    "eonet_category": category_title,
                    "magnitude": magnitude if isinstance(magnitude, int | float) else None,
                    "magnitude_unit": unit if isinstance(unit, str) else None,
                    "source": str(sources[0].get("id")) if sources else None,
                    "observations": len(geometries),
                }
            ),
            content_hash=content_hash(str(latest.get("date")), str(item.get("title")), str(url)),
        )

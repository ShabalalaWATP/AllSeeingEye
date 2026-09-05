"""USGS earthquakes: GeoJSON summary feed for the past day, updated every minute upstream."""

from __future__ import annotations

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
    id="usgs_earthquakes",
    name="USGS earthquakes (past day)",
    organisation="United States Geological Survey",
    category=Category.DISASTER,
    kind=SourceKind.GEOJSON,
    url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=5),
    licence_note="US public domain",
    homepage="https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
    instrument=True,
)

MAX_MAGNITUDE = 9.0


class UsgsConnector:
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
        features = data.get("features", []) if isinstance(data, dict) else []
        events = [event for feature in features if (event := self._to_event(feature, now))]
        return events

    def _to_event(self, feature: dict[str, Any], now: datetime) -> Event | None:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        upstream_id = feature.get("id")
        if len(coords) < 2 or not upstream_id:
            return None
        try:
            point = Point(lon=float(coords[0]), lat=float(coords[1]))
        except (TypeError, ValueError):
            return None
        depth_km = float(coords[2]) if len(coords) > 2 and coords[2] is not None else None
        magnitude = props.get("mag")
        place = props.get("place") or "unknown location"
        status = str(props.get("status") or "automatic")
        time_ms = props.get("time")
        published = (
            datetime.fromtimestamp(time_ms / 1000, tz=UTC) if isinstance(time_ms, int) else now
        )
        magnitude_value = float(magnitude) if isinstance(magnitude, int | float) else None
        title = (
            f"M{magnitude_value:.1f} {place}"
            if magnitude_value is not None
            else f"Earthquake, {place}"
        )
        severity = (
            min(1.0, max(0.0, magnitude_value / MAX_MAGNITUDE))
            if magnitude_value is not None
            else None
        )
        depth_text = f"Depth {depth_km:.0f} km. " if depth_km is not None else ""
        reviewed = status == "reviewed"
        return Event(
            id=event_id(self.spec.id, str(upstream_id)),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="earthquake",
            title=title,
            summary=f"{depth_text}Solution status: {status}.",
            url=props.get("url"),
            published_at=published,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"earthquake"}),
            severity=severity,
            reliability=self.spec.reliability,
            credibility=Credibility.CONFIRMED if reviewed else Credibility.PROBABLY_TRUE,
            grade_rationale=(
                "Instrument data from USGS, reviewed by an analyst"
                if reviewed
                else "Instrument data from USGS, automatic solution"
            ),
            attributes=freeze_attributes(
                {
                    "magnitude": magnitude_value,
                    "depth_km": depth_km,
                    "place": place,
                    "status": status,
                    "tsunami": bool(props.get("tsunami")),
                    "alert": props.get("alert"),
                    "felt": props.get("felt"),
                }
            ),
            content_hash=content_hash(str(props.get("updated")), str(magnitude), place, status),
        )

"""EMSC earthquakes (seismicportal.eu FDSN JSON): faster than USGS outside the United States."""

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
    id="emsc_earthquakes",
    name="EMSC earthquakes (M4+)",
    organisation="European-Mediterranean Seismological Centre",
    category=Category.DISASTER,
    kind=SourceKind.GEOJSON,
    url=(
        "https://www.seismicportal.eu/fdsnws/event/1/query"
        "?format=json&limit=200&minmag=4&orderby=time"
    ),
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=5),
    licence_note="CC BY 4.0, cite EMSC",
    homepage="https://www.seismicportal.eu/",
    instrument=True,
)
MAX_MAGNITUDE = 9.0


def _when(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class EmscConnector:
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
        return [event for feature in features if (event := self._to_event(feature, now))]

    def _to_event(self, feature: dict[str, Any], now: datetime) -> Event | None:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        unid = props.get("unid") or feature.get("id")
        if len(coords) < 2 or not unid:
            return None
        try:
            point = Point(lon=float(coords[0]), lat=float(coords[1]))
        except (TypeError, ValueError):
            return None
        magnitude = props.get("mag")
        magnitude_value = float(magnitude) if isinstance(magnitude, int | float) else None
        region = str(props.get("flynn_region") or "unknown region").title()
        depth = props.get("depth")
        title = f"M{magnitude_value:.1f} {region}" if magnitude_value else f"Earthquake, {region}"
        return Event(
            id=event_id(self.spec.id, str(unid)),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="earthquake",
            title=title,
            summary=(f"Depth {float(depth):.0f} km. " if isinstance(depth, int | float) else "")
            + f"Solution by {props.get('auth') or 'EMSC'}.",
            url=f"https://www.seismicportal.eu/eventdetails.html?unid={unid}",
            published_at=_when(props.get("time"), now),
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"earthquake"}),
            severity=(
                min(1.0, max(0.0, magnitude_value / MAX_MAGNITUDE))
                if magnitude_value is not None
                else None
            ),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Instrument data collated by EMSC from contributing networks",
            attributes=freeze_attributes(
                {
                    "magnitude": magnitude_value,
                    "magnitude_type": props.get("magtype"),
                    "depth_km": float(depth) if isinstance(depth, int | float) else None,
                    "region": region,
                    "authority": props.get("auth"),
                }
            ),
            content_hash=content_hash(str(unid), str(props.get("lastupdate")), str(magnitude)),
        )

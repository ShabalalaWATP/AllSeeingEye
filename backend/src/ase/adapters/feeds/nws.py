"""NOAA National Weather Service active alerts (extreme and severe) with polygons, US only."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.feeds.pipeline import strip_html
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
    id="nws_alerts",
    name="NWS severe weather alerts",
    organisation="NOAA National Weather Service",
    category=Category.DISASTER,
    kind=SourceKind.GEOJSON,
    url=(
        "https://api.weather.gov/alerts/active"
        "?status=actual&message_type=alert,update&severity=Extreme,Severe"
    ),
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=10),
    licence_note="US public domain; a User-Agent with contact is mandatory",
    homepage="https://www.weather.gov/",
)
SEVERITY = {"extreme": 0.8, "severe": 0.6}
MAX_ALERTS = 200


def _centroid(geometry: dict[str, Any] | None) -> Point | None:
    """The mean vertex of the first ring; alerts are small enough for that to be honest."""
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    ring: Any = None
    if kind == "Polygon" and coords:
        ring = coords[0]
    elif kind == "MultiPolygon" and coords and coords[0]:
        ring = coords[0][0]
    if not ring:
        return None
    try:
        lons = [float(vertex[0]) for vertex in ring]
        lats = [float(vertex[1]) for vertex in ring]
        return Point(lon=sum(lons) / len(lons), lat=sum(lats) / len(lats))
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _when(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


class NwsAlertsConnector:
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
        events = [
            event for feature in features[:MAX_ALERTS] if (event := self._to_event(feature, now))
        ]
        return events

    def _to_event(self, feature: dict[str, Any], now: datetime) -> Event | None:
        props = feature.get("properties") or {}
        alert_id = props.get("id") or feature.get("id")
        point = _centroid(feature.get("geometry"))
        if not alert_id or point is None:
            return None
        kind = str(props.get("event") or "Weather alert")
        severity = str(props.get("severity") or "").lower()
        headline = str(props.get("headline") or kind)
        return Event(
            id=event_id(self.spec.id, str(alert_id)),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="severe_weather",
            title=headline[:300],
            summary=(strip_html(str(props.get("description") or "")) or "")[:2_000] or None,
            url=str(props.get("@id") or f"https://api.weather.gov/alerts/{alert_id}"),
            published_at=_when(props.get("sent"), now),
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.CITY,
            country_iso="US",
            tags=frozenset({"severe_weather", re.sub(r"[^a-z0-9]+", "_", kind.lower()).strip("_")}),
            severity=SEVERITY.get(severity, 0.5),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Official warning from the issuing forecast office",
            attributes=freeze_attributes(
                {
                    "event": kind,
                    "severity": props.get("severity"),
                    "urgency": props.get("urgency"),
                    "certainty": props.get("certainty"),
                    "area": str(props.get("areaDesc") or "")[:500],
                    "sender": props.get("senderName"),
                    "expires": props.get("expires"),
                }
            ),
            content_hash=content_hash(
                str(alert_id), str(props.get("sent")), str(props.get("expires"))
            ),
        )

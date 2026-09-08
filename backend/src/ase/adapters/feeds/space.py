"""Space feeds: satellites propagated from CelesTrak elements, upcoming launches, the K index.

CelesTrak refreshes a group every two hours and answers 403 to earlier repeats, so the
elements are cached for that long while positions are propagated on every poll.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.adapters.feeds.satellites import SatelliteConnector, subpoint
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

__all__ = ["KpConnector", "LaunchConnector", "SatelliteConnector", "kp_severity", "subpoint"]

LAUNCHES = SourceSpec(
    id="launch_library",
    name="Upcoming launches (Launch Library 2)",
    organisation="The Space Devs",
    category=Category.SPACE,
    kind=SourceKind.API,
    url="https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=20&mode=normal",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=30),
    licence_note="Free tier, 15 requests an hour",
    homepage="https://thespacedevs.com/llapi",
)
KP = SourceSpec(
    id="swpc_kp",
    name="Planetary K index (NOAA SWPC)",
    organisation="NOAA Space Weather Prediction Center",
    category=Category.SPACE,
    kind=SourceKind.API,
    url="https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=15),
    licence_note="US public domain",
    homepage="https://www.swpc.noaa.gov/",
    instrument=True,
)


def kp_severity(kp: float) -> float:
    if kp >= 7:
        return 0.9
    if kp >= 6:
        return 0.7
    if kp >= 5:
        return 0.6
    if kp >= 4:
        return 0.4
    return 0.2


def _when(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


class LaunchConnector:
    spec = LAUNCHES

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        results = data.get("results", []) if isinstance(data, dict) else []
        return [
            event
            for item in results
            if isinstance(item, dict) and (event := self._to_event(item, now))
        ]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        launch_id = str(item.get("id") or "")
        name = str(item.get("name") or "").strip()
        pad = item.get("pad") or {}
        if not launch_id or not name:
            return None
        point: Point | None = None
        lat, lon = pad.get("latitude"), pad.get("longitude")
        if isinstance(lat, int | float) and isinstance(lon, int | float):
            try:
                point = Point(lon=float(lon), lat=float(lat))
            except ValueError:
                point = None
        net = _when(item.get("net"), now)
        status = (item.get("status") or {}).get("abbrev") or "TBD"
        provider = (item.get("launch_service_provider") or {}).get("name") or "unknown provider"
        location = (pad.get("location") or {}).get("name") or pad.get("name") or "unknown site"
        return Event(
            id=event_id(self.spec.id, launch_id),
            source_id=self.spec.id,
            category=Category.SPACE,
            subtype="launch",
            title=f"Launch: {name} ({provider}), {net:%Y-%m-%d %H:%M} UTC, {status}",
            summary=f"{provider} from {location}. Status {status}.",
            url=str(item.get("url") or self.spec.homepage),
            published_at=_when(item.get("last_updated"), now),
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT if point else GeoConfidence.NONE,
            tags=frozenset({"launch", status.lower()}),
            severity=0.3,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Launch schedule maintained from official announcements",
            attributes=freeze_attributes(
                {
                    "net": net.isoformat(),
                    "status": status,
                    "provider": provider,
                    "site": location,
                    "mission": (
                        (item.get("mission") or {}).get("name") if item.get("mission") else None
                    ),
                    "rocket": ((item.get("rocket") or {}).get("configuration") or {}).get(
                        "full_name"
                    ),
                }
            ),
            content_hash=content_hash(launch_id, net.isoformat(), status),
        )


class KpConnector:
    spec = KP

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        rows = [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []
        if not rows:
            return []
        latest = rows[-1]
        kp = latest.get("Kp")
        if not isinstance(kp, int | float):
            return []
        now = self._clock.now()
        level = "storm" if kp >= 5 else "active" if kp >= 4 else "quiet"
        return [
            Event(
                id=event_id(self.spec.id, "latest"),
                source_id=self.spec.id,
                category=Category.SPACE,
                subtype="geomagnetic",
                title=f"Planetary K index {kp:.2f}: {level}",
                summary=f"Three-hour planetary K index at {latest.get('time_tag')} UTC.",
                url="https://www.swpc.noaa.gov/products/planetary-k-index",
                published_at=_when(str(latest.get("time_tag") or "") + "+00:00", now),
                observed_at=now,
                geo_confidence=GeoConfidence.NONE,
                tags=frozenset({"geomagnetic", level}),
                severity=kp_severity(float(kp)),
                reliability=self.spec.reliability,
                credibility=Credibility.CONFIRMED,
                grade_rationale="Instrument index from the SWPC magnetometer network",
                attributes=freeze_attributes({"kp": float(kp), "time_tag": latest.get("time_tag")}),
                content_hash=content_hash(str(latest.get("time_tag")), str(kp)),
            )
        ]

"""Space feeds: satellites propagated from CelesTrak elements, upcoming launches, the K index.

CelesTrak refreshes a group every two hours and answers 403 to earlier repeats, so the
elements are cached for that long while positions are propagated on every poll.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sgp4 import omm
from sgp4.api import Satrec, jday

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

EARTH_RADIUS_KM = 6371.0
ELEMENT_TTL = timedelta(hours=2)
MAX_OBJECTS = 500

SATELLITES = SourceSpec(
    id="celestrak_stations",
    name="Space stations and crewed vehicles (CelesTrak)",
    organisation="CelesTrak",
    category=Category.SPACE,
    kind=SourceKind.API,
    url="https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=2),
    licence_note="Free under the CelesTrak usage policy; elements refresh every two hours",
    homepage="https://celestrak.org/",
    instrument=True,
)
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


def gmst_degrees(jd: float) -> float:
    return (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0


def subpoint(r: tuple[float, float, float], when: datetime) -> tuple[Point, float]:
    """The point beneath a TEME position vector and its altitude in kilometres."""
    x, y, z = r
    jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second)
    lon = (math.degrees(math.atan2(y, x)) - gmst_degrees(jd + fr) + 540.0) % 360.0 - 180.0
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    altitude = math.sqrt(x * x + y * y + z * z) - EARTH_RADIUS_KM
    return Point(lon=lon, lat=lat), altitude


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


class SatelliteConnector:
    """One moving event per object in a CelesTrak group."""

    def __init__(self, http: FeedHttpClient, clock: Clock, spec: SourceSpec = SATELLITES) -> None:
        self._http = http
        self._clock = clock
        self.spec = spec
        self._elements: list[dict[str, Any]] = []
        self._fetched_at: datetime | None = None

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        if self._fetched_at is None or now - self._fetched_at >= ELEMENT_TTL:
            try:
                data = await self._http.get_json(self.spec.url, conditional=False)
            except NotModified:
                data = self._elements
            self._elements = (
                [item for item in data if isinstance(item, dict)][:MAX_OBJECTS]
                if isinstance(data, list)
                else []
            )
            self._fetched_at = now
        return [event for fields in self._elements if (event := self._to_event(fields, now))]

    def _to_event(self, fields: dict[str, Any], now: datetime) -> Event | None:
        norad = str(fields.get("NORAD_CAT_ID") or "")
        name = str(fields.get("OBJECT_NAME") or norad)
        if not norad:
            return None
        satellite = Satrec()
        try:
            omm.initialize(satellite, {k: str(v) for k, v in fields.items()})
            jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
            error, r, v = satellite.sgp4(jd, fr)
        except (ValueError, TypeError, KeyError):
            return None
        if error != 0:
            return None
        try:
            point, altitude = subpoint(r, now)
        except ValueError:
            return None
        speed = math.sqrt(sum(component * component for component in v))
        return Event(
            id=event_id(self.spec.id, norad),
            source_id=self.spec.id,
            category=Category.SPACE,
            subtype="satellite",
            title=name,
            summary=(
                f"Altitude {altitude:.0f} km, {speed:.1f} km/s, propagated from elements of "
                f"{fields.get('EPOCH')}."
            ),
            url=f"https://celestrak.org/satcat/table-satcat.php?CATNR={norad}",
            published_at=now,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"satellite", "stations"}),
            severity=None,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Position propagated with SGP4 from published orbital elements",
            attributes=freeze_attributes(
                {
                    "norad_id": norad,
                    "object_id": fields.get("OBJECT_ID"),
                    "altitude_km": round(altitude, 1),
                    "speed_km_s": round(speed, 2),
                    "epoch": fields.get("EPOCH"),
                    "inclination_deg": fields.get("INCLINATION"),
                }
            ),
            content_hash=content_hash(norad, f"{point.lon:.2f}", f"{point.lat:.2f}"),
        )


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

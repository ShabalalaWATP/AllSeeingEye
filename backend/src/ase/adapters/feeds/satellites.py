"""Bounded public satellite catalogues and SGP4 position estimates."""

from __future__ import annotations

import asyncio
import csv
import io
import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import islice
from typing import Any

from sgp4 import omm
from sgp4.api import Satrec, jday

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
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
MAX_OBJECTS = 20_000
MAX_ELEMENT_AGE = timedelta(days=14)
STALE_ELEMENT_AGE = timedelta(days=3)

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
ACTIVE_SATELLITES = replace(
    SATELLITES,
    id="celestrak_active",
    name="Active satellites (CelesTrak)",
    url="https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv",
)
MILITARY_SATELLITES = replace(
    SATELLITES,
    id="celestrak_military",
    name="Public military satellite catalogue (CelesTrak)",
    url="https://celestrak.org/NORAD/elements/gp.php?GROUP=military&FORMAT=json",
)
SKYNET_SATELLITES = replace(
    SATELLITES,
    id="celestrak_skynet",
    name="Skynet public orbital elements (CelesTrak)",
    url="https://celestrak.org/NORAD/elements/gp.php?NAME=SKYNET&FORMAT=json",
)
SATELLITE_SPECS = (SATELLITES, ACTIVE_SATELLITES, MILITARY_SATELLITES, SKYNET_SATELLITES)


def orbital_epoch(value: object) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)


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


class SatelliteConnector:
    """One moving event per object in a CelesTrak group."""

    def __init__(self, http: FeedHttpClient, clock: Clock, spec: SourceSpec = SATELLITES) -> None:
        self._http = http
        self._clock = clock
        self.spec = spec
        self._elements: list[dict[str, Any]] = []
        self._fetched_at: datetime | None = None
        self._retry_at: datetime | None = None

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        if self._retry_at is not None and now < self._retry_at:
            raise FeedFetchError("CelesTrak retrieval failed; waiting two hours before retrying")
        if self._fetched_at is None or now - self._fetched_at >= ELEMENT_TTL:
            try:
                if "FORMAT=csv" in self.spec.url:
                    text = await self._http.get_text(self.spec.url, conditional=False)
                    reader = csv.DictReader(io.StringIO(text))
                    if not reader.fieldnames or "NORAD_CAT_ID" not in reader.fieldnames:
                        raise ValueError("Satellite catalogue is missing orbital fields")
                    data = list(islice(reader, MAX_OBJECTS))
                else:
                    data = await self._http.get_json(self.spec.url, conditional=False)
            except NotModified:
                data = self._elements
            except FeedFetchError:
                self._retry_at = now + ELEMENT_TTL
                raise
            self._retry_at = None
            self._elements = (
                [item for item in data if isinstance(item, dict)][:MAX_OBJECTS]
                if isinstance(data, list)
                else []
            )
            self._fetched_at = now
        events: dict[str, Event] = {}
        for index, fields in enumerate(self._elements):
            if event := self._to_event(fields, now):
                events[event.id] = event
            if (index + 1) % 250 == 0:
                await asyncio.sleep(0)
        return list(events.values())

    def _to_event(self, fields: dict[str, Any], now: datetime) -> Event | None:
        norad = str(fields.get("NORAD_CAT_ID") or "")
        name = str(fields.get("OBJECT_NAME") or norad)
        epoch = orbital_epoch(fields.get("EPOCH"))
        if (
            not 1 <= len(norad) <= 9
            or not norad.isascii()
            or not norad.isdigit()
            or not 0 < int(norad) < 1_000_000_000
            or epoch is None
            or now - epoch > MAX_ELEMENT_AGE
            or epoch - now > timedelta(days=1)
        ):
            return None
        name = name[:300]
        # A name search also returns launch hardware; do not label it as a Skynet satellite.
        if self.spec.id == SKYNET_SATELLITES.id and (
            not name.upper().startswith("SKYNET ")
            or any(marker in name.upper() for marker in (" R/B", " DEB"))
        ):
            return None
        satellite = Satrec()
        try:
            normalised = {k: str(v) for k, v in fields.items()}
            normalised["EPOCH"] = epoch.replace(tzinfo=None).isoformat(timespec="microseconds")
            omm.initialize(satellite, normalised)
            jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
            error, r, v = satellite.sgp4(jd, fr)
        except (ValueError, TypeError, KeyError):
            return None
        if error != 0 or not all(math.isfinite(value) for value in (*r, *v)):
            return None
        try:
            point, altitude = subpoint(r, now)
        except ValueError:
            return None
        speed = math.sqrt(sum(component * component for component in v))
        group = self.spec.id.removeprefix("celestrak_")
        skynet = name.upper().startswith("SKYNET ")
        military = group == "military" or skynet
        stale = abs(now - epoch) > STALE_ELEMENT_AGE
        tags = {"satellite", group, "propagated"}
        if military:
            tags.add("military-public")
        if skynet:
            tags.add("skynet")
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
            tags=frozenset(tags),
            severity=None,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale=(
                "Model estimate from public SGP4 elements, not a live observation. "
                + ("Elements are over three days old." if stale else "Element epoch shown.")
            ),
            attributes=freeze_attributes(
                {
                    "norad_id": norad,
                    "object_id": fields.get("OBJECT_ID"),
                    "altitude_km": round(altitude, 1),
                    "speed_km_s": round(speed, 2),
                    "epoch": fields.get("EPOCH"),
                    "inclination_deg": fields.get("INCLINATION"),
                    "catalogue_group": group,
                    "position_kind": "propagated",
                    "position_at": now.isoformat(),
                    "epoch_age_hours": round((now - epoch).total_seconds() / 3600, 2),
                    "is_stale": stale,
                    "military_public_catalogue": military,
                    "affiliation_basis": (
                        "Public Skynet satellite name"
                        if skynet
                        else "CelesTrak military group"
                        if military
                        else "Not classified"
                    ),
                }
            ),
            content_hash=content_hash(norad, f"{point.lon:.2f}", f"{point.lat:.2f}"),
        )

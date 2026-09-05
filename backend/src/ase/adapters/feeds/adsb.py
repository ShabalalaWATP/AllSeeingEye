"""Military aircraft positions from the adsb.lol community ADS-B network (v2 API, no key).

Each aircraft keeps one event id (its ICAO hex), so every poll moves the marker
rather than adding a new one, and the short aviation retention window drops
aircraft that stop reporting.
"""

from __future__ import annotations

from datetime import datetime, timedelta
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
    id="adsb_mil",
    name="Military aircraft (adsb.lol ADS-B)",
    organisation="adsb.lol community ADS-B network",
    category=Category.AVIATION,
    kind=SourceKind.API,
    url="https://api.adsb.lol/v2/mil",
    reliability=Reliability.B,
    poll_interval=timedelta(seconds=60),
    licence_note="Open Database Licence (ODbL); positions from volunteer receivers",
    homepage="https://adsb.lol/",
    instrument=True,
    flags=frozenset({"crowd_sourced"}),
)

MAX_AIRCRAFT = 2_000
MAX_POSITION_AGE_SECONDS = 600.0


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


class AdsbMilitaryConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url, conditional=False)
        except NotModified:
            return []
        aircraft = data.get("ac", []) if isinstance(data, dict) else []
        now = self._clock.now()
        events: list[Event] = []
        for item in aircraft[:MAX_AIRCRAFT]:
            if isinstance(item, dict) and (event := self._to_event(item, now)) is not None:
                events.append(event)
        return events

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        hex_code = _text(item.get("hex")).lower()
        lat, lon = _number(item.get("lat")), _number(item.get("lon"))
        if not hex_code or lat is None or lon is None:
            return None
        try:
            point = Point(lon=lon, lat=lat)
        except ValueError:
            return None
        age = _number(item.get("seen_pos")) or 0.0
        if age > MAX_POSITION_AGE_SECONDS:
            return None
        callsign = _text(item.get("flight"))
        registration = _text(item.get("r"))
        aircraft_type = _text(item.get("t"))
        label = callsign or registration or hex_code.upper()
        altitude = item.get("alt_baro")
        on_ground = altitude == "ground"
        altitude_ft = None if on_ground else _number(altitude)
        speed = _number(item.get("gs"))
        track = _number(item.get("track"))
        summary = (
            f"{'On the ground' if on_ground else 'Airborne'}"
            f"{f' at {int(altitude_ft)} ft' if altitude_ft is not None else ''}"
            f"{f', {int(speed)} kt' if speed is not None else ''}"
            f"{f', track {int(track)}°' if track is not None else ''}. "
            "Position from volunteer ADS-B receivers via adsb.lol."
        )
        tags = {"military", "adsb"}
        if aircraft_type:
            tags.add(aircraft_type.lower())
        return Event(
            id=event_id(self.spec.id, hex_code),
            source_id=self.spec.id,
            category=Category.AVIATION,
            subtype="military_aircraft",
            title=f"{label} ({aircraft_type})" if aircraft_type else label,
            summary=summary,
            url=f"https://globe.adsb.lol/?icao={hex_code}",
            published_at=now - timedelta(seconds=age),
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset(tags),
            severity=None,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale=(
                "Transponder position relayed by volunteer receivers; "
                "identity is whatever the aircraft broadcasts"
            ),
            attributes=freeze_attributes(
                {
                    "icao_hex": hex_code,
                    "callsign": callsign or None,
                    "registration": registration or None,
                    "aircraft_type": aircraft_type or None,
                    "altitude_ft": altitude_ft,
                    "on_ground": on_ground,
                    "ground_speed_kt": speed,
                    "track_deg": track,
                    "vertical_rate_fpm": _number(item.get("baro_rate")),
                    "squawk": _text(item.get("squawk")) or None,
                    "mlat": bool(item.get("mlat")),
                    "tisb": bool(item.get("tisb")),
                    "position_age_s": age,
                }
            ),
            content_hash=content_hash(
                hex_code, f"{lat:.4f}", f"{lon:.4f}", str(altitude), str(track), str(speed)
            ),
        )

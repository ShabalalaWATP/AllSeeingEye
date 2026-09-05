"""Aircraft positions from the adsb.lol community ADS-B network (v2 API, no key).

Each aircraft keeps one event id (its ICAO hex), so every poll moves the marker rather
than adding a new one, and the short aviation retention window drops aircraft that stop
reporting. The same record shape serves the military, LADD and PIA lists, the
emergency-squawk queries and the area queries, so one parser handles them all.
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

MAX_AIRCRAFT = 2_000
MAX_POSITION_AGE_SECONDS = 600.0
FLAG_MILITARY = 1
FLAG_INTERESTING = 2
FLAG_PIA = 4
FLAG_LADD = 8


def adsb_spec(
    source_id: str,
    name: str,
    url: str,
    *,
    seconds: int = 60,
    reliability: Reliability = Reliability.B,
) -> SourceSpec:
    return SourceSpec(
        id=source_id,
        name=name,
        organisation="adsb.lol community ADS-B network",
        category=Category.AVIATION,
        kind=SourceKind.API,
        url=url,
        reliability=reliability,
        poll_interval=timedelta(seconds=seconds),
        licence_note="Open Database Licence (ODbL); positions from volunteer receivers",
        homepage="https://adsb.lol/",
        instrument=True,
        flags=frozenset({"crowd_sourced"}),
    )


SPEC = adsb_spec("adsb_mil", "Military aircraft (adsb.lol ADS-B)", "https://api.adsb.lol/v2/mil")
LADD = adsb_spec(
    "adsb_ladd",
    "LADD aircraft (owners limiting display)",
    "https://api.adsb.lol/v2/ladd",
    seconds=120,
)
PIA = adsb_spec(
    "adsb_pia", "PIA aircraft (privacy ICAO addresses)", "https://api.adsb.lol/v2/pia", seconds=120
)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def flag_tags(item: dict[str, Any]) -> set[str]:
    """Tags from the adsb.lol database flags: military, interesting, PIA and LADD."""
    flags = _number(item.get("dbFlags")) or 0.0
    bits = int(flags)
    tags: set[str] = set()
    if bits & FLAG_MILITARY:
        tags.add("military")
    if bits & FLAG_INTERESTING:
        tags.add("interesting")
    if bits & FLAG_PIA:
        tags.add("pia")
    if bits & FLAG_LADD:
        tags.add("ladd")
    return tags


def aircraft_event(
    spec: SourceSpec,
    item: dict[str, Any],
    now: datetime,
    *,
    subtype: str,
    tags: frozenset[str],
    severity: float | None = None,
) -> Event | None:
    """One event per aircraft record, or None when it has no usable position."""
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
    squawk = _text(item.get("squawk")) or None
    summary = (
        f"{'On the ground' if on_ground else 'Airborne'}"
        f"{f' at {int(altitude_ft)} ft' if altitude_ft is not None else ''}"
        f"{f', {int(speed)} kt' if speed is not None else ''}"
        f"{f', track {int(track)}°' if track is not None else ''}"
        f"{f', squawk {squawk}' if squawk else ''}. "
        "Position from volunteer ADS-B receivers via adsb.lol."
    )
    all_tags = set(tags) | {"adsb"} | flag_tags(item)
    if aircraft_type:
        all_tags.add(aircraft_type.lower())
    # An aircraft seen over a watched area keeps its military identity, so the marker
    # does not flip between the military list and the area query.
    if subtype == "aircraft" and "military" in all_tags:
        subtype = "military_aircraft"
    return Event(
        id=event_id("adsb", hex_code),
        source_id=spec.id,
        category=Category.AVIATION,
        subtype=subtype,
        title=f"{label} ({aircraft_type})" if aircraft_type else label,
        summary=summary,
        url=f"https://globe.adsb.lol/?icao={hex_code}",
        published_at=now - timedelta(seconds=age),
        observed_at=now,
        point=point,
        geo_confidence=GeoConfidence.EXACT,
        tags=frozenset(all_tags),
        severity=severity,
        reliability=spec.reliability,
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
                "squawk": squawk,
                "emergency": _text(item.get("emergency")) or None,
                "nac_p": _number(item.get("nac_p")),
                "nic": _number(item.get("nic")),
                "mlat": bool(item.get("mlat")),
                "tisb": bool(item.get("tisb")),
                "position_age_s": age,
                "db_flags": int(_number(item.get("dbFlags")) or 0),
            }
        ),
        content_hash=content_hash(
            hex_code, f"{lat:.4f}", f"{lon:.4f}", str(altitude), str(track), str(speed), squawk
        ),
    )


def records(data: Any) -> list[dict[str, Any]]:
    aircraft = data.get("ac", []) if isinstance(data, dict) else []
    return [item for item in aircraft[:MAX_AIRCRAFT] if isinstance(item, dict)]


class AdsbListConnector:
    """One of adsb.lol's curated lists (military, LADD, PIA) as a category of aircraft."""

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        spec: SourceSpec = SPEC,
        *,
        subtype: str = "military_aircraft",
        tags: frozenset[str] = frozenset({"military"}),
    ) -> None:
        self._http = http
        self._clock = clock
        self.spec = spec
        self._subtype = subtype
        self._tags = tags

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url, conditional=False)
        except NotModified:
            return []
        now = self._clock.now()
        events = [
            aircraft_event(self.spec, item, now, subtype=self._subtype, tags=self._tags)
            for item in records(data)
        ]
        return [event for event in events if event is not None]


def AdsbMilitaryConnector(http: FeedHttpClient, clock: Clock) -> AdsbListConnector:  # noqa: N802
    """The original military list connector, kept under its old name."""
    return AdsbListConnector(http, clock, SPEC)

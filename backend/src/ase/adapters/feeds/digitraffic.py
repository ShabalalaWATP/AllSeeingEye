"""Latest regional AIS position records, attributed to Fintraffic's open data service."""

import math
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.application.feeds.budgets import VESSEL_POSITION_AGE
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Event,
    GeoConfidence,
    JsonScalar,
    Point,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

URL = "https://meri.digitraffic.fi/api/ais/v1/locations"
HOMEPAGE = "https://www.digitraffic.fi/en/marine-traffic/"
LICENCE = "https://creativecommons.org/licenses/by/4.0/"
MAX_RECORDS = 5_000
SPEC = SourceSpec(
    id="digitraffic_ais",
    name="Fintraffic AIS: Finnish waterways",
    organisation="Fintraffic / Digitraffic",
    category=Category.MARITIME,
    kind=SourceKind.GEOJSON,
    url=URL,
    homepage=HOMEPAGE,
    reliability=Reliability.F,
    poll_interval=timedelta(minutes=2),
    instrument=True,
    licence_note=(
        f"Fintraffic / Digitraffic, CC BY 4.0 ({LICENCE}); normalised, freshness-filtered."
    ),
    flags=frozenset({"ais", "regional_coverage", "reported_identity"}),
)
LIMITATIONS = (
    "AIS position reported through Fintraffic / Digitraffic, covering Finnish waterways. "
    "MMSI and movement are transmitted assertions, not verified identity or intent. "
    "The timestamp is the provider's location-record time. Coverage is incomplete; "
    "absence does not prove a vessel is absent. Normalised and freshness-filtered. "
    f"Source: {HOMEPAGE} Licence: CC BY 4.0, {LICENCE}"
)


def _integer(value: Any, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError
    return value


def _number(value: Any, maximum: float) -> float | None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    return float(value) if value < maximum else None


def _position(feature: Any, now: datetime) -> Event | None:
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError
    fields = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(fields, dict) or not isinstance(geometry, dict):
        raise ValueError
    mmsi = _integer(feature.get("mmsi"), 1, 999_999_999)
    if _integer(fields.get("mmsi"), 1, 999_999_999) != mmsi:
        raise ValueError
    timestamp = _integer(fields.get("timestampExternal"), 0, 10**15)
    recorded = datetime.fromtimestamp(timestamp / 1000, UTC)
    if not now - VESSEL_POSITION_AGE <= recorded <= now + timedelta(seconds=30):
        return None
    coords = geometry.get("coordinates")
    if geometry.get("type") != "Point" or not isinstance(coords, list) or len(coords) != 2:
        raise ValueError
    if any(type(value) not in (int, float) for value in coords):
        raise ValueError
    # AIS unavailable coordinates (181/91) are not positions. Never map them to zero.
    try:
        point = Point(lon=float(coords[0]), lat=float(coords[1]))
    except ValueError:
        return None
    heading = _number(fields.get("heading"), 360)
    course = _number(fields.get("cog"), 360)
    speed = _number(fields.get("sog"), 102.3)
    attributes: dict[str, JsonScalar] = {
        "mmsi": f"{mmsi:09d}",
        "position_record_time": recorded.isoformat(),
        "timestamp_kind": "provider_location_record",
        "coverage": "Finnish waterways",
        "heading_deg": heading,
        "course_over_ground_deg": course,
        "track_deg": heading if heading is not None else course,
        "orientation_basis": "heading"
        if heading is not None
        else "course"
        if course is not None
        else "unknown",
        "speed_over_ground_knots": speed,
        "navigation_status_code": _integer(fields.get("navStat"), 0, 15),
        "ais_timestamp_code": _integer(fields.get("timestamp"), 0, 63),
        "position_accuracy_high": fields.get("posAcc")
        if type(fields.get("posAcc")) is bool
        else None,
        "raim": fields.get("raim") if type(fields.get("raim")) is bool else None,
        "attribution": "Fintraffic / Digitraffic",
        "licence_url": LICENCE,
        "source_url": HOMEPAGE,
        "modifications": "Normalised and freshness-filtered",
    }
    return Event(
        id=event_id(SPEC.id, f"{mmsi:09d}"),
        source_id=SPEC.id,
        category=Category.MARITIME,
        subtype="vessel_position",
        title=f"AIS vessel {mmsi:09d}",
        summary=LIMITATIONS,
        url=f"{URL}?mmsi={mmsi}",
        published_at=recorded,
        observed_at=now,
        point=point,
        geo_confidence=GeoConfidence.EXACT,
        reliability=Reliability.F,
        grade_rationale="Unassessed reliability; reported AIS identity may be wrong or spoofed.",
        attributes=freeze_attributes(attributes),
        tags=frozenset({"ais", "regional_coverage"}),
        content_hash=content_hash(
            str(timestamp), repr(point), *[str(value) for value in attributes.values()]
        ),
    )


def parse_locations(data: Any, now: datetime) -> list[Event]:
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise FeedFetchError("Digitraffic returned an invalid collection")
    rows = data.get("features")
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
        raise FeedFetchError("Digitraffic collection is invalid or exceeds the record limit")
    events: dict[str, Event] = {}
    try:
        for row in rows:
            event = _position(row, now)
            if event is not None:
                previous = events.get(event.id)
                if previous is None or (
                    previous.published_at is not None
                    and event.published_at is not None
                    and previous.published_at < event.published_at
                ):
                    events[event.id] = event
    except (ValueError, OverflowError, OSError):
        raise FeedFetchError("Digitraffic returned an invalid vessel record") from None
    return list(events.values())


class DigitrafficConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        query = urlencode(
            {
                "from": int((now - VESSEL_POSITION_AGE).timestamp() * 1000),
                "to": int(now.timestamp() * 1000),
            }
        )
        data = await self._http.get_json(f"{URL}?{query}", conditional=False, max_redirects=0)
        return parse_locations(data, self._clock.now())

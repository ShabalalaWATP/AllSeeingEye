"""Normalise the documented combined snapshot without trusting broadcast identities."""

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.barentswatch_http import LATEST_URL
from ase.adapters.feeds.http import FeedFetchError
from ase.application.feeds.budgets import VESSEL_POSITION_AGE
from ase.application.feeds.pipeline import clean_text
from ase.domain.events import (
    Category,
    Event,
    GeoConfidence,
    Point,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)

SOURCE_ID = "barentswatch_ais"
HOMEPAGE = "https://www.barentswatch.no/"
MAX_RECORDS = 20_000
COVERAGE = "Norwegian economic zone and the protection zones around Svalbard and Jan Mayen"
LIMITATIONS = (
    f"Norwegian Coastal Administration AIS via BarentsWatch. Regional coverage: {COVERAGE}. "
    "Excludes fishing vessels under 15 metres and leisure/sailing vessels under 45 metres. "
    "AIS identity, type and movement are transmitted assertions and may be spoofed. "
    "Missing positions do not prove absence. Snapshot polling, normalised and freshness-filtered."
)


def _number(value: Any, maximum: float) -> float | None:
    if type(value) not in (int, float) or not 0 <= value < maximum:
        return None
    return float(value) if math.isfinite(value) else None


def _position(row: Any, now: datetime) -> Event | None:
    if not isinstance(row, dict):
        return None
    try:
        mmsi = row.get("mmsi")
        if type(mmsi) is not int or not 1 <= mmsi <= 999_999_999:
            raise ValueError
        lat, lon = row["latitude"], row["longitude"]
        if type(lat) not in (int, float) or type(lon) not in (int, float):
            raise ValueError
        point = Point(lat=lat, lon=lon)
        raw_time = row.get("msgtime")
        if not isinstance(raw_time, str) or len(raw_time) > 64:
            raise ValueError
        recorded = datetime.fromisoformat(raw_time)
        if recorded.tzinfo is None:
            raise ValueError
        recorded = recorded.astimezone(UTC)
        if not now - VESSEL_POSITION_AGE <= recorded <= now + timedelta(seconds=30):
            raise ValueError
        name = row.get("name")
        title = clean_text(name[:300] if isinstance(name, str) else None, 150)
        heading, course = (
            _number(row.get("trueHeading"), 360),
            _number(row.get("courseOverGround"), 360),
        )
        ship_type = row.get("shipType")
        ship_type = ship_type if type(ship_type) is int and 1 <= ship_type <= 99 else None
        navigation_status = row.get("navigationalStatus")
        navigation_status = (
            navigation_status
            if type(navigation_status) is int and 0 <= navigation_status < 15
            else None
        )
        military = ship_type == 35
        attrs = freeze_attributes(
            {
                "mmsi": f"{mmsi:09d}",
                "ship_name": title,
                "coverage": COVERAGE,
                "position_record_time": recorded.isoformat(),
                "timestamp_kind": "provider_location_record",
                "heading_deg": heading,
                "course_over_ground_deg": course,
                "track_deg": heading if heading is not None else course,
                "orientation_basis": "heading"
                if heading is not None
                else "course"
                if course is not None
                else "unknown",
                "speed_over_ground_knots": _number(row.get("speedOverGround"), 102.3),
                "navigation_status_code": navigation_status,
                "ship_type_code": ship_type,
                "ship_type_label": "Reported military operations"
                if military
                else "Reported law enforcement"
                if ship_type == 55
                else "Reported AIS ship type"
                if ship_type is not None
                else None,
                "military": military,
                "military_classification_basis": "reported_ais_ship_type_35" if military else None,
                # The combined response does not date its static vessel-type message.
                "ship_type_timestamp_kind": "static_message_time_unavailable",
                "attribution": "Norwegian Coastal Administration / BarentsWatch",
                "delivery_credit": "Data delivered by BarentsWatch",
                "licence": "NLOD",
                "licence_url": "https://www.barentswatch.no/en/articles/api-terms-and-conditions/",
                "modifications": "Normalised and freshness-filtered",
                "source_url": HOMEPAGE,
                "collection_mode": "Bounded snapshot polling",
            }
        )
        return Event(
            id=event_id(SOURCE_ID, f"{mmsi:09d}"),
            source_id=SOURCE_ID,
            category=Category.MARITIME,
            subtype="vessel_position",
            title=title or f"AIS vessel {mmsi:09d}",
            summary=LIMITATIONS,
            url=LATEST_URL,
            published_at=recorded,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            reliability=Reliability.F,
            grade_rationale="Unassessed AIS reports; identity, classification and position "
            "may be spoofed.",
            attributes=attrs,
            tags=frozenset({"ais", "regional_coverage"} | ({"military"} if military else set())),
            content_hash=content_hash(recorded.isoformat(), repr(point), repr(attrs)),
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def parse_positions(data: Any, now: datetime) -> list[Event]:
    if not isinstance(data, list) or len(data) > MAX_RECORDS:
        raise FeedFetchError("BarentsWatch snapshot is invalid or exceeds the record limit.")
    events: dict[str, Event] = {}
    for row in data:
        event = _position(row, now)
        if event is None:
            continue
        previous = events.get(event.id)
        if previous is None or (previous.published_at or now) < (event.published_at or now):
            events[event.id] = event
    return list(events.values())

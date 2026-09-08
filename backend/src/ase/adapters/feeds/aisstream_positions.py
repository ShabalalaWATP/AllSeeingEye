"""Validate AIS identities, current positions and AIS unavailable sentinel values."""

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.application.feeds.budgets import VESSEL_POSITION_AGE
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

_TYPES = {"PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"}


def _number(value: Any, maximum: float) -> float | None:
    return (
        float(value)
        if (type(value) in (float, int) and math.isfinite(value) and 0 <= value < maximum)
        else None
    )


def parse_position(data: dict[str, Any], now: datetime) -> Event | None:
    kind = data.get("MessageType")
    if not isinstance(kind, str) or kind not in _TYPES:
        return None
    try:
        metadata = data["MetaData"]
        report = data["Message"][kind]
        if not isinstance(metadata, dict) or not isinstance(report, dict):
            raise ValueError
        mmsi = metadata["MMSI"]
        if type(mmsi) is not int or not 1 <= mmsi <= 999_999_999:
            raise ValueError
        if report.get("UserID") != mmsi or report.get("Valid") is not True:
            raise ValueError
        # Use the position report, never metadata's potentially older last-known location.
        lat, lon = report["Latitude"], report["Longitude"]
        if type(lat) not in (int, float) or type(lon) not in (int, float):
            raise ValueError
        point = Point(lat=lat, lon=lon)
        raw_time = metadata["time_utc"]
        if not isinstance(raw_time, str) or len(raw_time) > 64:
            raise ValueError
        recorded = datetime.fromisoformat(raw_time.removesuffix(" UTC").replace(" +0000", "+00:00"))
        if recorded.tzinfo is None:
            raise ValueError
        recorded = recorded.astimezone(UTC)
        if not now - VESSEL_POSITION_AGE <= recorded <= now + timedelta(seconds=30):
            raise ValueError
        name = metadata.get("ShipName")
        title = name.strip()[:150] if isinstance(name, str) else ""
        heading = _number(report.get("TrueHeading"), 360)
        course = _number(report.get("Cog"), 360)
        attrs = freeze_attributes(
            {
                "mmsi": f"{mmsi:09d}",
                "coverage": "Global receiver coverage, incomplete",
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
                "speed_over_ground_knots": _number(report.get("Sog"), 102.3),
                "attribution": "AISStream",
                "source_url": "https://aisstream.io/",
                "collection_mode": "Bounded stream sampling",
                "message_type": kind,
            }
        )
        return Event(
            id=event_id("aisstream", str(mmsi)),
            source_id="aisstream",
            category=Category.MARITIME,
            subtype="vessel_position",
            title=title or f"AIS vessel {mmsi:09d}",
            summary="AISStream ship position. Coverage is incomplete and sampled. "
            "AIS identity and movement are transmitted assertions, not verified facts.",
            url="https://aisstream.io/",
            published_at=recorded,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            reliability=Reliability.F,
            grade_rationale="Unassessed AIS reports; identity and position may be spoofed.",
            attributes=attrs,
            tags=frozenset({"ais", "global_coverage", "sampled"}),
            content_hash=content_hash(str(recorded), repr(point), repr(attrs)),
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

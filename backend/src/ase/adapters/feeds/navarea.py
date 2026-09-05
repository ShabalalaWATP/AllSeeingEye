"""NAVAREA and HYDROARC broadcast warnings from the US NGA Maritime Safety Information API.

Positions are written into the warning text in the form 39-16.00N 076-35.00W, so the
first one becomes the marker and the count of positions travels with the event. Verified
live on 5 September 2026 (386 active warnings, 362 with a position).
"""

from __future__ import annotations

import re
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
    id="nga_navarea",
    name="NAVAREA broadcast warnings (NGA MSI)",
    organisation="US National Geospatial-Intelligence Agency, Maritime Safety Information",
    category=Category.MARITIME,
    kind=SourceKind.API,
    url="https://msi.nga.mil/api/publications/broadcast-warn?status=active&output=json",
    reliability=Reliability.A,
    poll_interval=timedelta(hours=2),
    licence_note="US Government work",
    homepage="https://msi.nga.mil/NavWarnings",
)

POSITION = re.compile(r"(\d{2})-(\d{2}(?:\.\d+)?)([NS])\s+(\d{3})-(\d{2}(?:\.\d+)?)([EW])")
ISSUE = re.compile(r"(\d{2})(\d{2})(\d{2})Z\s+([A-Z]{3})\s+(\d{4})")
MONTHS = {
    m: i
    for i, m in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1
    )
}
KINDS: tuple[tuple[str, re.Pattern[str], float], ...] = (
    ("security", re.compile(r"PIRA|ARMED|ATTACK|SUSPICIOUS|ROBBER|HIJACK", re.I), 0.8),
    ("gnss", re.compile(r"GNSS|GPS|INTERFERENCE|JAMMING|SPOOF", re.I), 0.7),
    (
        "military_exercise",
        re.compile(r"GUNNERY|FIRING|EXERCISE|MISSILE|ROCKET|LIVE FIRE|HAZARDOUS OPERATIONS", re.I),
        0.6,
    ),
    (
        "hazard",
        re.compile(r"DRILLING|MOBILE OFFSHORE|CABLE|BUOY|LIGHT|DERELICT|WRECK|CASUALTY", re.I),
        0.3,
    ),
)
MAX_WARNINGS = 1_000


def positions(text: str) -> list[Point]:
    found: list[Point] = []
    for match in POSITION.finditer(text):
        lat = int(match.group(1)) + float(match.group(2)) / 60
        lon = int(match.group(4)) + float(match.group(5)) / 60
        if match.group(3) == "S":
            lat = -lat
        if match.group(6) == "W":
            lon = -lon
        try:
            found.append(Point(lon=lon, lat=lat))
        except ValueError:
            continue
    return found


def issued(value: str, fallback: datetime) -> datetime:
    match = ISSUE.search(value or "")
    if match is None or match.group(4) not in MONTHS:
        return fallback
    try:
        return datetime(
            int(match.group(5)),
            MONTHS[match.group(4)],
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            tzinfo=UTC,
        )
    except ValueError:
        return fallback


def kind_of(text: str) -> tuple[str, float]:
    for name, pattern, severity in KINDS:
        if pattern.search(text):
            return name, severity
    return "navigation", 0.3


class NavareaConnector:
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
        warnings = data.get("broadcast-warn", []) if isinstance(data, dict) else []
        return [
            event
            for item in warnings[:MAX_WARNINGS]
            if isinstance(item, dict) and (event := self._to_event(item, now))
        ]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        area = str(item.get("navArea") or "").strip()
        year = str(item.get("msgYear") or "").strip()
        number = str(item.get("msgNumber") or "").strip()
        text = " ".join(str(item.get("text") or "").split())
        if not (area and year and number and text):
            return None
        points = positions(text)
        kind, severity = kind_of(text)
        headline = text.split(". ")[0][:120]
        return Event(
            id=event_id(self.spec.id, f"{area}-{year}-{number}"),
            source_id=self.spec.id,
            category=Category.MARITIME,
            subtype="navarea_warning",
            title=f"NAVAREA {area} {year}/{number}: {headline}",
            summary=text[:2_000],
            url=f"https://msi.nga.mil/NavWarnings?navArea={area}",
            published_at=issued(str(item.get("issueDate") or ""), now),
            observed_at=now,
            point=points[0] if points else None,
            geo_confidence=GeoConfidence.EXACT if points else GeoConfidence.NONE,
            tags=frozenset({"navarea", f"navarea_{area.lower()}", kind}),
            severity=severity,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Official broadcast warning relayed by the NGA",
            attributes=freeze_attributes(
                {
                    "nav_area": area,
                    "message": f"{year}/{number}",
                    "subregion": item.get("subregion"),
                    "authority": item.get("authority"),
                    "kind": kind,
                    "positions": len(points),
                    "status": item.get("status"),
                }
            ),
            content_hash=content_hash(area, year, number, str(item.get("status")), text[:200]),
        )

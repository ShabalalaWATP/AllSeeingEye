"""GDACS multi-hazard alerts (earthquake, cyclone, flood, volcano, drought, wildfire, tsunami)."""

from __future__ import annotations

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# Types only: parsing goes through defusedxml below.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.ElementTree import fromstring as safe_fromstring

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

SPEC = SourceSpec(
    id="gdacs",
    name="GDACS disaster alerts",
    organisation="Global Disaster Alert and Coordination System (EC JRC, UN OCHA)",
    category=Category.DISASTER,
    kind=SourceKind.RSS,
    url="https://www.gdacs.org/xml/rss.xml",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=10),
    licence_note="Feed declares public domain; JRC terms of use apply",
    homepage="https://www.gdacs.org/",
    instrument=True,
)

NS = {"gdacs": "http://www.gdacs.org", "georss": "http://www.georss.org/georss"}
EVENT_TYPES = {
    "EQ": "earthquake",
    "TC": "tropical_cyclone",
    "FL": "flood",
    "VO": "volcano",
    "DR": "drought",
    "WF": "wildfire",
    "TS": "tsunami",
}
ALERT_SEVERITY = {"green": 0.3, "orange": 0.6, "red": 0.9}


def _text(item: Element, path: str) -> str:
    return (item.findtext(path, default="", namespaces=NS) or "").strip()


def _parse_date(value: str) -> datetime | None:
    try:
        return parsedate_to_datetime(value) if value else None
    except (TypeError, ValueError):
        return None


def _point(item: Element) -> Point | None:
    raw = _text(item, "georss:point").split()
    if len(raw) != 2:
        return None
    try:
        return Point(lon=float(raw[1]), lat=float(raw[0]))
    except ValueError:
        return None


class GdacsConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            text = await self._http.get_text(self.spec.url)
        except NotModified:
            return []
        try:
            root: Element = safe_fromstring(text.lstrip("﻿").encode("utf-8"))
        except ParseError as exc:
            raise FeedFetchError("GDACS feed is not well-formed XML") from exc
        now = self._clock.now()
        items = root.findall("./channel/item")
        return [event for item in items if (event := self._to_event(item, now))]

    def _to_event(self, item: Element, now: datetime) -> Event | None:
        guid = _text(item, "guid") or _text(item, "gdacs:eventid")
        point = _point(item)
        if not guid or point is None:
            return None
        event_type = _text(item, "gdacs:eventtype").upper()
        subtype = EVENT_TYPES.get(event_type, event_type.lower() or "alert")
        alert = _text(item, "gdacs:alertlevel") or "Green"
        name = _text(item, "gdacs:eventname") or _text(item, "gdacs:country") or "unnamed"
        severity_node = item.find("gdacs:severity", NS)
        population_node = item.find("gdacs:population", NS)
        modified = _text(item, "gdacs:datemodified")
        published = _parse_date(_text(item, "pubDate")) or _parse_date(modified) or now
        return Event(
            id=event_id(self.spec.id, guid),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype=subtype,
            title=f"{alert} alert, {subtype.replace('_', ' ')}: {name}",
            summary=_text(item, "description") or _text(item, "title"),
            url=_text(item, "link") or self.spec.homepage,
            published_at=published,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT if event_type == "EQ" else GeoConfidence.CITY,
            tags=frozenset({subtype, f"gdacs_{alert.lower()}"}),
            severity=ALERT_SEVERITY.get(alert.lower(), 0.3),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="GDACS automated impact assessment from official monitoring feeds",
            attributes=freeze_attributes(
                {
                    "alert_level": alert,
                    "alert_score": _text(item, "gdacs:alertscore"),
                    "event_type": event_type,
                    "event_name": name,
                    "episode_id": _text(item, "gdacs:episodeid"),
                    "iso3": _text(item, "gdacs:iso3"),
                    "country": _text(item, "gdacs:country"),
                    "severity_text": (severity_node.text or "").strip()
                    if severity_node is not None
                    else "",
                    "severity_value": severity_node.get("value")
                    if severity_node is not None
                    else None,
                    "population_text": (population_node.text or "").strip()
                    if population_node is not None
                    else "",
                    "from_date": _text(item, "gdacs:fromdate"),
                    "to_date": _text(item, "gdacs:todate"),
                }
            ),
            content_hash=content_hash(guid, modified, alert, _text(item, "gdacs:episodeid")),
        )

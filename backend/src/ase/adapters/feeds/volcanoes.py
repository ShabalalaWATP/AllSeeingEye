"""Smithsonian and USGS weekly volcanic activity report, one event per volcano reported."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

# Types only: parsing goes through defusedxml below.
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.ElementTree import fromstring as safe_fromstring

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.feeds.rss import child_text, link_of, parse_feed_date, point_of
from ase.application.feeds.pipeline import strip_html
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

SPEC = SourceSpec(
    id="gvp_weekly",
    name="Smithsonian weekly volcanic activity report",
    organisation="Smithsonian Institution Global Volcanism Program and USGS",
    category=Category.DISASTER,
    kind=SourceKind.RSS,
    url="https://volcano.si.edu/news/WeeklyVolcanoRSS.xml",
    reliability=Reliability.A,
    poll_interval=timedelta(hours=6),
    licence_note="Smithsonian Institution; cite the Global Volcanism Program",
    homepage="https://volcano.si.edu/reports_weekly.cfm",
)

TITLE = re.compile(
    r"^(?P<volcano>.+?) \((?P<country>[^)]+)\) - Report for (?P<period>.+?) - (?P<activity>.+)$"
)
SEVERITY = {"new eruptive activity": 0.6, "ongoing activity": 0.4}


class VolcanoReportConnector:
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
            raise FeedFetchError("Volcano report feed is not well-formed XML") from exc
        now = self._clock.now()
        return [event for item in root.iter("item") if (event := self._to_event(item, now))]

    def _to_event(self, item: Element, now: datetime) -> Event | None:
        title = child_text(item, "title")
        guid = child_text(item, "guid")
        point = point_of(item)
        match = TITLE.match(title)
        if not guid or point is None or match is None:
            return None
        activity = match.group("activity").strip()
        key = activity.lower()
        return Event(
            id=event_id(self.spec.id, guid),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="volcano",
            title=f"{match.group('volcano')}, {match.group('country')}: {activity.lower()}",
            summary=(strip_html(child_text(item, "description")) or "")[:2_000] or None,
            url=guid if guid.startswith("http") else link_of(item) or self.spec.homepage,
            published_at=parse_feed_date(child_text(item, "pubDate")) or now,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"volcano", key.replace(" ", "_")}),
            severity=SEVERITY.get(key, 0.4),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Weekly report compiled from volcano observatories",
            attributes=freeze_attributes(
                {
                    "volcano": match.group("volcano"),
                    "country": match.group("country"),
                    "period": match.group("period"),
                    "activity": activity,
                }
            ),
            content_hash=content_hash(guid, match.group("period"), activity),
        )

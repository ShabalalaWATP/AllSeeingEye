"""Tsunami bulletins from the US National and Pacific Tsunami Warning Centres (Atom with CAP)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

# Types only: parsing goes through defusedxml below.
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.ElementTree import fromstring as safe_fromstring

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.feeds.rss import child_text, children, parse_feed_date, point_of
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


def _spec(centre: str, name: str, url: str) -> SourceSpec:
    return SourceSpec(
        id=f"{centre}_tsunami",
        name=name,
        organisation="NOAA National Weather Service tsunami warning centres",
        category=Category.DISASTER,
        kind=SourceKind.RSS,
        url=url,
        reliability=Reliability.A,
        poll_interval=timedelta(minutes=10),
        licence_note="US public domain",
        homepage="https://www.tsunami.gov/",
        instrument=True,
    )


NTWC = _spec(
    "ntwc",
    "National Tsunami Warning Center bulletins",
    "https://www.tsunami.gov/events/xml/PAAQAtom.xml",
)
PTWC = _spec(
    "ptwc",
    "Pacific Tsunami Warning Center bulletins",
    "https://www.tsunami.gov/events/xml/PHEBAtom.xml",
)

CATEGORY = re.compile(r"Category:\s*([A-Za-z]+)")
MAGNITUDE = re.compile(r"Magnitude:\s*([\d.]+)")
SEVERITY = {"information": 0.2, "advisory": 0.6, "watch": 0.7, "warning": 0.9}


def _summary_text(entry: Element) -> str:
    for child in children(entry, "summary"):
        return " ".join(piece.strip() for piece in child.itertext() if piece.strip())
    return ""


def _bulletin_link(entry: Element) -> str | None:
    for child in children(entry, "link"):
        href = (child.get("href") or "").strip()
        if href and child.get("rel") in (None, "alternate", "related"):
            return href
    for child in children(entry, "summary"):
        for anchor in child.iter():
            target = anchor.get("href")
            if target and anchor.tag.rsplit("}", 1)[-1] == "a":
                return target
    return None


class TsunamiConnector:
    def __init__(self, http: FeedHttpClient, clock: Clock, spec: SourceSpec = NTWC) -> None:
        self._http = http
        self._clock = clock
        self.spec = spec

    async def fetch(self) -> list[Event]:
        try:
            text = await self._http.get_text(self.spec.url)
        except NotModified:
            return []
        try:
            root: Element = safe_fromstring(text.lstrip("﻿").encode("utf-8"))
        except ParseError as exc:
            raise FeedFetchError("Tsunami feed is not well-formed XML") from exc
        now = self._clock.now()
        entries = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "entry"]
        return [event for entry in entries if (event := self._to_event(entry, now))]

    def _to_event(self, entry: Element, now: datetime) -> Event | None:
        entry_id = child_text(entry, "id")
        region = child_text(entry, "title")
        point = point_of(entry)
        if not entry_id or not region or point is None:
            return None
        summary = _summary_text(entry)
        category = CATEGORY.search(summary)
        kind = category.group(1).lower() if category else "information"
        magnitude = MAGNITUDE.search(summary)
        return Event(
            id=event_id(self.spec.id, entry_id),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="tsunami",
            title=f"Tsunami {kind}: {region}",
            summary=summary[:2_000] or None,
            url=_bulletin_link(entry) or self.spec.homepage,
            published_at=parse_feed_date(child_text(entry, "updated")) or now,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"tsunami", kind}),
            severity=SEVERITY.get(kind, 0.5),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Official warning centre bulletin",
            attributes=freeze_attributes(
                {
                    "bulletin_category": kind,
                    "magnitude": float(magnitude.group(1)) if magnitude else None,
                    "region": region,
                }
            ),
            content_hash=content_hash(entry_id, child_text(entry, "updated"), kind),
        )

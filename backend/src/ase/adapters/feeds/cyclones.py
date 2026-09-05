"""Tropical cyclones: NHC advisories (Atlantic, East Pacific) and JTWC warnings (West Pacific,
Indian Ocean, southern hemisphere). Both verified live on 5 September 2026."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

# Types only: parsing goes through defusedxml below.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.ElementTree import fromstring as safe_fromstring

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.feeds.rss import child_text, children, link_of, parse_feed_date
from ase.application.feeds.pipeline import strip_html
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

KNOTS_PER_MPH = 0.868976
MAX_JTWC_PRODUCTS = 8
JTWC_PRODUCTS = "https://www.metoc.navy.mil/jtwc/products/"
JTWC_BASINS = {"wp": "west_pacific", "io": "indian_ocean", "sh": "southern_hemisphere"}


def _nhc_spec(basin: str, name: str, url: str) -> SourceSpec:
    return SourceSpec(
        id=f"nhc_{basin}",
        name=name,
        organisation="NOAA National Hurricane Center",
        category=Category.DISASTER,
        kind=SourceKind.RSS,
        url=url,
        reliability=Reliability.A,
        poll_interval=timedelta(minutes=30),
        licence_note="US public domain",
        homepage="https://www.nhc.noaa.gov/",
        instrument=True,
    )


NHC_ATLANTIC = _nhc_spec(
    "atlantic", "NHC Atlantic advisories", "https://www.nhc.noaa.gov/index-at.xml"
)
NHC_EAST_PACIFIC = _nhc_spec(
    "east_pacific", "NHC Eastern Pacific advisories", "https://www.nhc.noaa.gov/index-ep.xml"
)
JTWC = SourceSpec(
    id="jtwc",
    name="JTWC tropical cyclone warnings",
    organisation="US Joint Typhoon Warning Center",
    category=Category.DISASTER,
    kind=SourceKind.RSS,
    url="https://www.metoc.navy.mil/jtwc/rss/jtwc.rss",
    reliability=Reliability.A,
    poll_interval=timedelta(hours=1),
    licence_note="US public domain",
    homepage="https://www.metoc.navy.mil/jtwc/jtwc.html",
    instrument=True,
)


def severity_from_knots(knots: float | None) -> float:
    """Saffir-Simpson-shaped scale: depression 0.4, storm 0.5, then one step per category."""
    if knots is None:
        return 0.4
    steps = ((34, 0.4), (64, 0.5), (83, 0.6), (96, 0.7), (113, 0.8), (137, 0.9))
    for limit, value in steps:
        if knots < limit:
            return value
    return 1.0


def _parse_xml(text: str, name: str) -> Element:
    try:
        root: Element = safe_fromstring(text.lstrip("﻿").encode("utf-8"))
    except ParseError as exc:
        raise FeedFetchError(f"{name} feed is not well-formed XML") from exc
    return root


class NhcConnector:
    """One event per active cyclone, from the `nhc:Cyclone` block of each summary item."""

    def __init__(self, http: FeedHttpClient, clock: Clock, spec: SourceSpec = NHC_ATLANTIC) -> None:
        self._http = http
        self._clock = clock
        self.spec = spec

    async def fetch(self) -> list[Event]:
        try:
            text = await self._http.get_text(self.spec.url)
        except NotModified:
            return []
        root = _parse_xml(text, "NHC")
        now = self._clock.now()
        events: list[Event] = []
        for item in root.iter("item"):
            for cyclone in children(item, "Cyclone"):
                event = self._to_event(item, cyclone, now)
                if event is not None:
                    events.append(event)
        return events

    def _to_event(self, item: Element, cyclone: Element, now: datetime) -> Event | None:
        centre = child_text(cyclone, "center").replace(",", " ").split()
        atcf = child_text(cyclone, "atcf")
        if len(centre) != 2 or not atcf:
            return None
        try:
            point = Point(lon=float(centre[1]), lat=float(centre[0]))
        except ValueError:
            return None
        kind = child_text(cyclone, "type") or "Tropical cyclone"
        name = child_text(cyclone, "name") or atcf
        wind = child_text(cyclone, "wind")
        pressure = child_text(cyclone, "pressure")
        movement = child_text(cyclone, "movement")
        headline = child_text(cyclone, "headline").strip(". ")
        mph = re.search(r"(\d+)\s*mph", wind, re.IGNORECASE)
        knots = float(mph.group(1)) * KNOTS_PER_MPH if mph else None
        when = child_text(cyclone, "datetime")
        title = f"{kind} {name}: {headline}" if headline else f"{kind} {name}"
        return Event(
            id=event_id(self.spec.id, atcf),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="tropical_cyclone",
            title=title,
            summary=(strip_html(child_text(item, "description")) or "")[:2_000] or None,
            url=link_of(item) or self.spec.homepage,
            published_at=parse_feed_date(child_text(item, "pubDate")) or now,
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"tropical_cyclone", kind.lower().replace(" ", "_")}),
            severity=severity_from_knots(knots),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Official forecast centre advisory",
            attributes=freeze_attributes(
                {
                    "type": kind,
                    "name": name,
                    "atcf": atcf,
                    "wallet": child_text(cyclone, "wallet"),
                    "wind": wind,
                    "pressure": pressure,
                    "movement": movement,
                    "advisory_time": when,
                }
            ),
            content_hash=content_hash(atcf, when, wind, pressure, movement),
        )


NAME_LINE = re.compile(
    r"(SUPER TYPHOON|TYPHOON|TROPICAL STORM|TROPICAL DEPRESSION|TROPICAL CYCLONE|HURRICANE)"
    r"\s+(\d{2}[A-Z])\s*\(([^)]*)\)\s+WARNING NR\s+(\d+)"
)
POSITION = re.compile(r"(\d{6})Z\s*-+\s*NEAR\s+(\d+\.\d)([NS])\s+(\d+\.\d)([EW])")
WINDS = re.compile(r"MAX SUSTAINED WINDS - (\d+) KT")
MOVEMENT = re.compile(r"MOVEMENT PAST SIX HOURS - (\d+) DEGREES AT (\d+) KTS")
PRODUCT = re.compile(r"([a-z]{2}\d{4})web\.txt")


def _dtg(value: str, now: datetime) -> datetime:
    """A JTWC day-hour-minute group ('050600') in the current month, or last month."""
    day, hour, minute = int(value[:2]), int(value[2:4]), int(value[4:6])
    try:
        when = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return now
    if when > now + timedelta(days=1):
        first = now.replace(day=1)
        previous = (first - timedelta(days=1)).replace(day=1)
        try:
            when = previous.replace(day=day, hour=hour, minute=minute)
        except ValueError:
            return now
    return when.astimezone(UTC)


class JtwcConnector:
    """The RSS lists active systems; each warning text carries the position and winds."""

    spec = JTWC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            rss = await self._http.get_text(self.spec.url)
        except NotModified:
            return []
        products = list(dict.fromkeys(PRODUCT.findall(rss)))[:MAX_JTWC_PRODUCTS]
        now = self._clock.now()
        events: list[Event] = []
        for product in products:
            try:
                text = await self._http.get_text(
                    f"{JTWC_PRODUCTS}{product}web.txt", conditional=False
                )
            except (FeedFetchError, NotModified):
                continue
            event = self._to_event(product, text, now)
            if event is not None:
                events.append(event)
        return events

    def _to_event(self, product: str, text: str, now: datetime) -> Event | None:
        name = NAME_LINE.search(text)
        position = POSITION.search(text)
        if name is None or position is None:
            return None
        lat = float(position.group(2)) * (1 if position.group(3) == "N" else -1)
        lon = float(position.group(4)) * (1 if position.group(5) == "E" else -1)
        try:
            point = Point(lon=lon, lat=lat)
        except ValueError:
            return None
        winds = WINDS.search(text)
        knots = float(winds.group(1)) if winds else None
        movement = MOVEMENT.search(text)
        kind = name.group(1).title()
        designation, storm, number = name.group(2), name.group(3).title(), name.group(4)
        basin = JTWC_BASINS.get(product[:2], product[:2])
        return Event(
            id=event_id(self.spec.id, product),
            source_id=self.spec.id,
            category=Category.DISASTER,
            subtype="tropical_cyclone",
            title=f"{kind} {designation} ({storm}), warning {number}",
            summary=(
                f"Position {position.group(2)}{position.group(3)} {position.group(4)}"
                f"{position.group(5)} at {position.group(1)}Z."
                + (f" Maximum sustained winds {int(knots)} kt." if knots is not None else "")
                + (
                    f" Moving {movement.group(1)} degrees at {movement.group(2)} kt."
                    if movement
                    else ""
                )
            ),
            url=f"{JTWC_PRODUCTS}{product}web.txt",
            published_at=_dtg(position.group(1), now),
            observed_at=now,
            point=point,
            geo_confidence=GeoConfidence.EXACT,
            tags=frozenset({"tropical_cyclone", kind.lower().replace(" ", "_"), basin}),
            severity=severity_from_knots(knots),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Official warning centre product",
            attributes=freeze_attributes(
                {
                    "type": kind,
                    "designation": designation,
                    "name": storm,
                    "warning_number": number,
                    "wind_knots": knots,
                    "basin": basin,
                }
            ),
            content_hash=content_hash(product, number),
        )

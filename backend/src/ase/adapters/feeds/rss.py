"""One connector for RSS 2.0, RSS 1.0 (RDF) and Atom feeds, configured by a source seed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

# Types only: parsing goes through defusedxml below.
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.ElementTree import fromstring as safe_fromstring

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.feeds.pipeline import strip_html
from ase.application.ports import Clock
from ase.domain.events import (
    Credibility,
    Event,
    GeoConfidence,
    Point,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceSpec

MAX_ITEMS = 200
ITEM_TAGS = frozenset({"item", "entry"})
DATE_TAGS = ("pubDate", "published", "updated", "date", "dc:date")
BODY_TAGS = ("description", "summary", "content", "encoded")


@dataclass(frozen=True, slots=True)
class RssOptions:
    """How one feed's items become events; the seed decides, the connector applies."""

    subtype: str = "article"
    tags: frozenset[str] = frozenset()
    credibility: Credibility = Credibility.POSSIBLY_TRUE
    rationale: str = "Single-outlet report, not yet corroborated"
    # RSS <category domain="..."> whose text is an ISO 3166-1 alpha-2 country code.
    country_category_domain: str | None = None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(item: Element, *names: str) -> list[Element]:
    return [child for child in item if _local(child.tag) in names]


def _child_text(item: Element, *names: str) -> str:
    for child in _children(item, *names):
        text = "".join(child.itertext()).strip()
        if text:
            return text
    return ""


def _link(item: Element) -> str:
    for child in _children(item, "link"):
        href = (child.get("href") or "").strip()
        if href and child.get("rel", "alternate") == "alternate":
            return href
        if not href and child.text and child.text.strip():
            return child.text.strip()
    return ""


def parse_feed_date(value: str) -> datetime | None:
    """RFC 822 (RSS) or ISO 8601 (Atom, Dublin Core) to an aware UTC datetime."""
    if not value:
        return None
    parsed: datetime | None = None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _point(item: Element) -> Point | None:
    raw = _child_text(item, "point").split()
    if len(raw) == 2:
        lat, lon = raw
    else:
        lat, lon = _child_text(item, "lat"), _child_text(item, "long")
    try:
        return Point(lon=float(lon), lat=float(lat)) if lat and lon else None
    except ValueError:
        return None


def _country(item: Element, domain: str | None) -> str | None:
    if domain is None:
        return None
    for child in _children(item, "category"):
        code = (child.text or "").strip().upper()
        if child.get("domain") == domain and len(code) == 2 and code.isalpha():
            return code
    return None


def _categories(item: Element) -> list[str]:
    names: list[str] = []
    for child in _children(item, "category"):
        text = (child.get("term") or child.text or "").strip()
        if text and text not in names:
            names.append(text)
    return names[:10]


class RssConnector:
    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        spec: SourceSpec,
        options: RssOptions | None = None,
    ) -> None:
        self.spec = spec
        self._options = options or RssOptions()
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
            raise FeedFetchError(f"{self.spec.id}: feed is not well-formed XML") from exc
        now = self._clock.now()
        items = [element for element in root.iter() if _local(element.tag) in ITEM_TAGS]
        events = [event for item in items[:MAX_ITEMS] if (event := self._to_event(item, now))]
        return events

    def _to_event(self, item: Element, now: datetime) -> Event | None:
        link = _link(item)
        key = _child_text(item, "guid", "id") or link
        title = _child_text(item, "title")
        if not key or not title:
            return None
        summary = strip_html(_child_text(item, *BODY_TAGS))
        published = parse_feed_date(_child_text(item, *DATE_TAGS)) or now
        point = _point(item)
        country = _country(item, self._options.country_category_domain)
        if point is not None:
            confidence = GeoConfidence.EXACT
        elif country is not None:
            confidence = GeoConfidence.COUNTRY
        else:
            confidence = GeoConfidence.NONE
        author = _child_text(item, "creator", "author")
        return Event(
            id=event_id(self.spec.id, key),
            source_id=self.spec.id,
            category=self.spec.category,
            subtype=self._options.subtype,
            title=title,
            summary=summary,
            url=link or None,
            published_at=published,
            observed_at=now,
            language=self.spec.language,
            point=point,
            geo_confidence=confidence,
            country_iso=country,
            tags=self._options.tags | {self._options.subtype},
            severity=None,
            reliability=self.spec.reliability,
            credibility=self._options.credibility,
            grade_rationale=self._options.rationale,
            attributes=freeze_attributes(
                {
                    "outlet": self.spec.name,
                    "author": author[:120] or None,
                    "categories": ", ".join(_categories(item))[:200] or None,
                }
            ),
            content_hash=content_hash(key, title, summary, published.isoformat()),
        )

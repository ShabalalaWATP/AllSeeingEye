"""One connector for RSS 2.0, RSS 1.0 (RDF) and Atom feeds, configured by a source seed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from heapq import nlargest
from itertools import islice

# Types only: parsing goes through defusedxml below.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.ElementTree import fromstring as safe_fromstring

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.feeds.rss_access import REFUSAL_RECHECK, automation_refusal
from ase.application.feeds.pipeline import strip_html
from ase.application.ports import Clock
from ase.application.ports.feed_diagnostics import FeedBlocked
from ase.domain.events import (
    Credibility,
    Event,
    GeoConfidence,
    Point,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.source_dates import Calendar, DateBasis, DateRole, SourceDate, resolve_source_date
from ase.domain.sources import SourceSpec

MAX_ITEMS = 200
ITEM_TAGS = frozenset({"item", "entry"})
DC_TERMS = "http://purl.org/dc/terms/"
DC_ELEMENTS = "http://purl.org/dc/elements/1.1/"
ATOM = "http://www.w3.org/2005/Atom"
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
    headlines_only: bool = False
    newest_first: bool = False


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


def _looks_like_html(body: str) -> bool:
    """Error, consent and firewall pages often arrive with HTTP 200 in place of a feed."""
    head = body[:512].lstrip().lower()
    return head.startswith(("<!doctype html", "<html"))


def parse_feed_date(value: str) -> datetime | None:
    """RFC 822 (RSS) or ISO 8601 (Atom, Dublin Core) to an aware UTC datetime."""
    if not value or len(value) > 300:
        return None
    return resolve_source_date(value, "feed_date", "gregorian", basis="source_spec").value


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


def feed_source_dates(item: Element) -> tuple[SourceDate, ...]:
    # Exact vocabularies establish roles; generic lifecycle dates are not publication.
    declarations: list[SourceDate] = []
    ordered = sorted(item, key=lambda child: _date_priority(child.tag))
    for child in ordered:
        local = _local(child.tag)
        if local not in {"pubDate", "published", "issued", "updated", "date"}:
            continue
        raw = "".join(child.itertext())
        if not raw.strip() or len(raw) > 300 or len(child.tag) > 120:
            continue
        role: DateRole = "unspecified"
        calendar: Calendar = "unknown"
        basis: DateBasis = "source_metadata"
        if _date_priority(child.tag) == 0:
            role, calendar, basis = "publication", "gregorian", "source_spec"
        elif child.tag in {"updated", f"{{{ATOM}}}updated"}:
            role, calendar, basis = "modification", "gregorian", "source_spec"
        elif child.tag in {f"{{{DC_TERMS}}}date", f"{{{DC_ELEMENTS}}}date"}:
            calendar, basis = "gregorian", "source_spec"
        declarations.append(resolve_source_date(raw, child.tag, calendar, basis=basis, role=role))
        if len(declarations) == 4:
            break
    return tuple(declarations)


def _date_priority(tag: str) -> int:
    return (
        0 if tag in {"pubDate", "published", f"{{{ATOM}}}published", f"{{{DC_TERMS}}}issued"} else 1
    )


def feed_publication(item: Element) -> datetime | None:
    return next((row.value for row in feed_source_dates(item) if row.role == "publication"), None)


def select_feed_items(root: Element, *, newest_first: bool) -> tuple[list[Element], int]:
    """Select at most MAX_ITEMS within the HTTP byte cap, without an archive-sized list."""
    count = sum(_local(element.tag) in ITEM_TAGS for element in root.iter())
    items = (element for element in root.iter() if _local(element.tag) in ITEM_TAGS)
    selected = (
        nlargest(
            MAX_ITEMS,
            items,
            key=lambda item: feed_publication(item) or datetime.min.replace(tzinfo=UTC),
        )
        if newest_first
        else list(islice(items, MAX_ITEMS))
    )
    return selected, count


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
        except FeedFetchError as exc:
            reason = automation_refusal(self.spec.id, exc)
            if reason is None:
                raise
            raise FeedBlocked(reason, self._clock.now() + REFUSAL_RECHECK) from None
        body = text.lstrip("\ufeff")
        if _looks_like_html(body):
            raise FeedFetchError(f"{self.spec.id}: returned an HTML page, not an RSS or Atom feed")
        try:
            root: Element = safe_fromstring(body.encode("utf-8"))
        except ParseError as exc:
            raise FeedFetchError(f"{self.spec.id}: feed is not well-formed XML") from exc
        if _local(root.tag) not in {"rss", "RDF", "feed"}:
            raise FeedFetchError(f"{self.spec.id}: response is not an RSS or Atom feed")
        now = self._clock.now()
        selected, count = select_feed_items(root, newest_first=self._options.newest_first)
        events = [event for item in selected if (event := self._to_event(item, now))]
        if count > MAX_ITEMS:
            events = [
                event.with_changes(
                    attributes=freeze_attributes(
                        {
                            **event.attributes,
                            "feed_items_available": count,
                            "feed_items_limit": MAX_ITEMS,
                            "feed_items_truncated": True,
                        }
                    )
                )
                for event in events
            ]
        return events

    def _to_event(self, item: Element, now: datetime) -> Event | None:
        link = _link(item)
        key = _child_text(item, "guid", "id") or link
        title = _child_text(item, "title")
        if not key or not title:
            return None
        summary = (
            None if self._options.headlines_only else strip_html(_child_text(item, *BODY_TAGS))
        )
        source_dates = feed_source_dates(item)
        published = feed_publication(item)
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
            source_dates=source_dates,
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
            content_hash=content_hash(
                key, title, summary, published.isoformat() if published else None
            ),
        )


# Shared with the other XML connectors so each one does not grow its own copy.
children = _children
child_text = _child_text
point_of = _point
link_of = _link

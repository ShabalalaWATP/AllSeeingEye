"""Fresh EONET candidates with dated original point or polygon evidence."""

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.eonet import SPEC
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.feed import web_url
from ase.adapters.research.hazard_area import (
    HazardArea,
    collect,
    instant,
    number,
    page_limit,
    supports,
)
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Point,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.observation import ObservationMetadata
from ase.domain.research import ResearchBatch, ResearchQuery

SOURCE_ID = "research-eonet-area"
ENDPOINT = "https://eonet.gsfc.nasa.gov/api/v3/events"
LIMITATIONS = (
    "One current EONET catalogue page, open and closed events, at most 50 quick or 100 detailed "
    "candidates. Exact local polygon/multipolygon intersection of dated source geometry. "
    "Upstream bounding-box datapoint filtering may omit overlapping extents. Latest matching "
    "observation per event only; no full track or historical completeness. Dates are often "
    "day-level midnight estimates. Question/language terms do not filter these area records. "
    "An empty result does not establish absence of hazards."
)


def request_url(query: ResearchQuery, area: HazardArea) -> str:
    west, south, east, north = area.bounds
    return (
        ENDPOINT
        + "?"
        + urlencode(
            {
                "status": "all",
                "start": query.since.astimezone(UTC).date().isoformat(),
                "end": query.until.astimezone(UTC).date().isoformat(),
                "bbox": f"{west},{north},{east},{south}",
                "limit": page_limit(query) + 1,
            }
        )
    )


class EonetAreaResearchProvider:
    id = SOURCE_ID
    name = "NASA EONET area hazard search"
    temporal_scope = "Geometry observation time, half-open interval of at most 14 days."
    spatial_scope = LIMITATIONS

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return supports(query)

    def supports_area(self, query: ResearchQuery) -> bool:
        return self.supports(query)

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        return await collect(
            self._http,
            self._clock,
            query,
            self.id,
            self.name,
            self.spatial_scope,
            request_url,
            self._parse,
        )

    def _parse(
        self, data: Any, query: ResearchQuery, area: HazardArea, now: datetime
    ) -> tuple[tuple[Event, ...], str]:
        items = data.get("events") if isinstance(data, dict) else None
        limit = page_limit(query)
        if not isinstance(items, list) or len(items) > limit + 1:
            raise ValueError("Invalid or oversized EONET events page")
        events: dict[str, Event] = {}
        rejected = 0
        for item in items[:limit]:
            try:
                event = self._event(item, query, area, now)
            except (TypeError, ValueError, IndexError, KeyError, OverflowError):
                event = None
            if event is None:
                rejected += 1
            else:
                events[event.id] = event
        detail = f"{rejected} candidates excluded by location, date or validation. "
        if len(items) > limit:
            detail += "Truncated page; additional events were not fetched. "
        return tuple(events.values()), detail

    def _event(
        self, item: Any, query: ResearchQuery, area: HazardArea, now: datetime
    ) -> Event | None:
        if not isinstance(item, dict):
            return None
        key, observations = item.get("id"), item.get("geometry")
        if not isinstance(key, str) or not key or len(key) > 200:
            return None
        if not isinstance(observations, list) or not 1 <= len(observations) <= 256:
            return None
        latest = None
        for raw in observations:
            if not isinstance(raw, dict):
                continue
            date = instant(raw.get("date"))
            if date is None or not query.since <= date < query.until:
                continue
            try:
                geometry = area.intersecting_geometry(raw, SPEC.id, SPEC.organisation)
            except (TypeError, ValueError, OverflowError):
                continue
            if geometry is not None and (latest is None or date > latest[0]):
                latest = date, geometry, raw
        if latest is None:
            return None
        acquired, geometry, raw = latest
        coordinates = geometry.to_geometry()["coordinates"]
        is_point = raw.get("type") == "Point"
        categories = item.get("categories")
        category = categories[0] if isinstance(categories, list) and categories else {}
        if not isinstance(category, dict):
            return None
        category_id = str(category.get("id") or "natural_event")[:80]
        subtype = re.sub(r"(?<!^)(?=[A-Z])", "_", category_id).lower()
        title = str(item.get("title") or "NASA EONET natural event")[:300]
        sources = item.get("sources")
        source = sources[0] if isinstance(sources, list) and sources else {}
        if not isinstance(source, dict):
            source = {}
        url = web_url(str(source.get("url") or "")) or web_url(str(item.get("link") or ""))
        return Event(
            id=event_id(SPEC.id, key),
            source_id=SPEC.id,
            category=Category.DISASTER,
            subtype=subtype,
            title=title,
            summary=str(item.get("description") or "Curated natural event from NASA EONET.")[:2000],
            url=url,
            published_at=None,
            observed_at=now,
            reliability=SPEC.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Curated NASA EONET event; cited upstream sources are not "
            "independent confirmations.",
            point=Point(*coordinates) if is_point else None,
            geo_confidence=GeoConfidence.EXACT if is_point else GeoConfidence.NONE,
            tags=frozenset({subtype}),
            geometry=geometry,
            observation=ObservationMetadata(
                acquired_at=acquired,
                collection_id=SPEC.id,
                item_id=key,
                limitations="Source geometry date, often midnight with day-level precision; "
                "not retrieval time. Latest matching observation in the requested area/interval. "
                "Reported event extent is not a confirmed impact or fire perimeter.",
            ),
            attributes=freeze_attributes(
                {
                    "eonet_category": str(category.get("title") or category_id),
                    "source": str(source.get("id") or "unknown"),
                    "magnitude": number(raw.get("magnitudeValue")),
                    "magnitude_unit": str(raw.get("magnitudeUnit") or "")[:100],
                    "closed": str(item.get("closed")) if item.get("closed") else None,
                    "collection_capability": self.id,
                    "observations": len(observations),
                }
            ),
            content_hash=content_hash(title, acquired.isoformat(), geometry.sha256, url),
        )

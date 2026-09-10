"""One USGS FDSN catalogue request, followed by exact local area/time filtering."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.usgs import SPEC, UsgsConnector
from ase.adapters.research.feed import web_url
from ase.adapters.research.hazard_area import HazardArea, collect, number, page_limit, supports
from ase.application.ports import Clock
from ase.domain.events import Event, content_hash, freeze_attributes
from ase.domain.observation import ObservationMetadata
from ase.domain.research import ResearchBatch, ResearchQuery

SOURCE_ID = "research-usgs-area"
ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"
LIMITATIONS = (
    "One current USGS earthquake catalogue page, at most 50 quick or 100 detailed candidates. "
    "Exact polygon/multipolygon intersection and origin-time interval, at most 14 days. "
    "Question/language terms do not filter this area query. Catalogue revisions, monitoring "
    "coverage and page limits prevent a complete historical account; no results do not "
    "establish absence of earthquakes."
)


def request_url(query: ResearchQuery, area: HazardArea) -> str:
    west, south, east, north = area.bounds
    return (
        ENDPOINT
        + "?"
        + urlencode(
            {
                "format": "geojson",
                "starttime": query.since.astimezone(UTC).isoformat(),
                "endtime": query.until.astimezone(UTC).isoformat(),
                "minlongitude": west,
                "maxlongitude": east,
                "minlatitude": south,
                "maxlatitude": north,
                "eventtype": "earthquake",
                "orderby": "time",
                "limit": page_limit(query) + 1,
            }
        )
    )


class UsgsAreaResearchProvider:
    id = SOURCE_ID
    name = "USGS area earthquake search"
    temporal_scope = "Earthquake origin time, half-open interval of at most 14 days."
    spatial_scope = LIMITATIONS

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock
        self._parser = UsgsConnector(http, clock)

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
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            raise ValueError("Expected USGS GeoJSON")
        features = data.get("features")
        limit = page_limit(query)
        if not isinstance(features, list) or len(features) > limit + 1:
            raise ValueError("USGS ignored the requested page bound")
        events: dict[str, Event] = {}
        rejected = 0
        for feature in features[:limit]:
            try:
                event = self._event(feature, query, area, now)
            except (ValueError, TypeError, KeyError, IndexError, OverflowError):
                event = None
            if event is None:
                rejected += 1
            else:
                events[event.id] = event
        detail = f"{rejected} candidates excluded by location, date or validation. "
        if len(features) > limit:
            detail += "Truncated page; additional events were not fetched. "
        return tuple(events.values()), detail

    def _event(
        self, feature: Any, query: ResearchQuery, area: HazardArea, now: datetime
    ) -> Event | None:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Expected an earthquake feature")
        key, props, raw = feature.get("id"), feature.get("properties"), feature.get("geometry")
        if not isinstance(key, str) or not key or len(key) > 200:
            raise ValueError("Invalid earthquake identifier")
        if not isinstance(props, dict) or not isinstance(raw, dict) or raw.get("type") != "Point":
            raise ValueError("Expected earthquake properties and a point")
        coords, time_ms = raw.get("coordinates"), props.get("time")
        if not isinstance(coords, list) or not 2 <= len(coords) <= 3:
            raise ValueError("Invalid earthquake coordinates")
        if type(time_ms) is not int or props.get("type") != "earthquake":
            return None
        acquired = datetime.fromtimestamp(time_ms / 1000, UTC)
        if not query.since <= acquired < query.until:
            return None
        if any(number(value) is None for value in coords):
            return None
        geometry = area.intersecting_geometry(
            {"type": "Point", "coordinates": coords[:2]}, SPEC.id, SPEC.organisation
        )
        if geometry is None:
            return None
        clean = dict(props)
        clean.update(
            place=str(props.get("place") or "unknown location")[:250],
            mag=number(props.get("mag")),
            status="reviewed" if props.get("status") == "reviewed" else "automatic",
            url=web_url(str(props.get("url") or "")),
            alert=props.get("alert")
            if props.get("alert") in ("green", "yellow", "orange", "red")
            else None,
            felt=number(props.get("felt")),
        )
        event = self._parser._to_event({**feature, "properties": clean}, now)
        if event is None:
            return None
        return replace(
            event,
            published_at=None,
            geometry=geometry,
            observation=ObservationMetadata(
                acquired_at=acquired,
                collection_id=SPEC.id,
                item_id=key,
                limitations="Earthquake origin time, not publication or retrieval. "
                "Instrument-derived epicentre is subject to solution uncertainty and revisions.",
            ),
            attributes=freeze_attributes({**event.attributes, "collection_capability": self.id}),
            content_hash=content_hash(event.content_hash, geometry.sha256, acquired.isoformat()),
        )

"""One bounded Overpass request: the named kinds of map feature inside a research area.

OpenStreetMap is the reference layer behind Bellingcat's osm-search. Here a question that
names feature kinds (a church, a railway station, a bridge) and carries a drawn area asks
Overpass once for those kinds inside the area's box, keeps only the features that fall
inside the exact polygon, and returns each as a located, cited item. The map's current
state is what comes back: nothing here says the feature existed on a given date.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from functools import partial
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.http_contracts import FeedHttpStatusError
from ase.adapters.research.hazard_area import MAX_BODY_BYTES, HazardArea, receipt
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Point,
    Reliability,
    event_id,
    freeze_attributes,
)
from ase.domain.osm_features import FeatureClass, classes_for
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.research_area import ResearchArea

SOURCE_ID = "research-osm-features"
NAME = "OpenStreetMap feature search"
ORGANISATION = "OpenStreetMap contributors"
ENDPOINT = "https://overpass-api.de/api/interpreter"
MAX_FEATURES = 100
MAX_AREA_KM2 = 5_000.0
TIMEOUT_SECONDS = 25
LIMITATIONS = (
    "One Overpass request for the feature kinds the question names, at most 100 features "
    "inside the drawn area, from OpenStreetMap's current state. Presence, names and tags are "
    "volunteer-entered and undated; a feature found is a candidate for a scene, not proof of "
    "it, and a feature missing from the map is not absent from the ground. Areas over "
    "5,000 square kilometres are not searched. Data is ODbL 1.0, credit OpenStreetMap "
    "contributors."
)
TEMPORAL_SCOPE = "Current map state at retrieval; no history and no event dates."
FAILED_TEXT = "Map features could not be retrieved or validated within their bounds."
_TAG_LIMIT = 12
_TAG_KEYS = (
    "name",
    "name:en",
    "amenity",
    "railway",
    "man_made",
    "power",
    "aeroway",
    "leisure",
    "historic",
    "landuse",
    "military",
    "waterway",
    "natural",
    "tourism",
    "office",
    "religion",
    "operator",
    "height",
)


def area_km2(bounds: tuple[float, float, float, float]) -> float:
    west, south, east, north = bounds
    mid = math.radians((south + north) / 2)
    return abs(east - west) * 111.32 * math.cos(mid) * abs(north - south) * 110.57


def question_text(query: ResearchQuery) -> str:
    return " ".join((query.question, *query.terms))


def supports(query: ResearchQuery) -> bool:
    return (
        query.area is not None
        and query.focus is ResearchFocus.GENERAL
        and bool(classes_for(question_text(query)))
    )


def overpass_query(
    classes: tuple[FeatureClass, ...], bounds: tuple[float, float, float, float]
) -> str:
    west, south, east, north = bounds
    box = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    selectors = "".join(f"nwr{filters};" for feature in classes for filters in feature.filters)
    head = f"[out:json][timeout:{TIMEOUT_SECONDS}][bbox:{box}];"
    return f"{head}({selectors});out center tags {MAX_FEATURES};"


def request_url(
    classes: tuple[FeatureClass, ...], bounds: tuple[float, float, float, float]
) -> str:
    return ENDPOINT + "?" + urlencode({"data": overpass_query(classes, bounds)})


class _AreaTooLarge(Exception):
    pass


class OsmFeaturesResearchProvider:
    id = SOURCE_ID
    name = NAME
    temporal_scope = TEMPORAL_SCOPE
    spatial_scope = LIMITATIONS

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return supports(query)

    def supports_area(self, query: ResearchQuery) -> bool:
        return supports(query)

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not supports(query) or query.area is None:
            return receipt(self.id, self.name, CollectionStatus.UNSUPPORTED, LIMITATIONS)
        classes = classes_for(question_text(query))
        try:
            items, detail = await self._fetch(query.area, classes)
        except _AreaTooLarge:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "The drawn area is larger than the 5,000 square kilometre map search bound.",
            )
        except TimeoutError:
            return receipt(
                self.id, self.name, CollectionStatus.TIMED_OUT, "The map request timed out."
            )
        except FeedHttpStatusError as error:
            return self._declined(error)
        except Exception:
            # Provider errors can include the operator's area; expose no error bodies or URLs.
            return receipt(self.id, self.name, CollectionStatus.FAILED, FAILED_TEXT)
        looked_for = ", ".join(feature.label.lower() for feature in classes)
        explanation = f"Looked for: {looked_for}. {detail}{LIMITATIONS}"
        status = CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY
        return receipt(self.id, self.name, status, explanation, items)

    async def _fetch(
        self, research_area: ResearchArea, classes: tuple[FeatureClass, ...]
    ) -> tuple[tuple[Event, ...], str]:
        area = await joined_thread_call(partial(HazardArea, research_area))
        west, south, east, north = area.bounds
        bounds = (west, south, east, north)
        if area_km2(bounds) > MAX_AREA_KM2:
            raise _AreaTooLarge
        body = await self._http.get_bytes(
            request_url(classes, bounds), conditional=False, max_redirects=0
        )
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("Overpass response exceeds admission byte limit")

        def project() -> tuple[tuple[Event, ...], str]:
            return parse(json.loads(body), classes, area, self._clock.now())

        return await joined_thread_call(project)

    def _declined(self, error: FeedHttpStatusError) -> ResearchBatch:
        # The public Overpass servers shed load with these; the map is not at fault.
        if error.status_code in (429, 503, 504):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "The public OpenStreetMap query server was busy and declined the request; "
                "a later run may succeed.",
            )
        return receipt(self.id, self.name, CollectionStatus.FAILED, FAILED_TEXT)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            spatial_scope=self.spatial_scope,
            temporal_scope=self.temporal_scope,
        )


def parse(
    data: Any, classes: tuple[FeatureClass, ...], area: HazardArea, now: datetime
) -> tuple[tuple[Event, ...], str]:
    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
        raise ValueError("Expected an Overpass JSON document")
    elements = data["elements"]
    if len(elements) > MAX_FEATURES:
        raise ValueError("Overpass ignored the requested feature bound")
    events: dict[str, Event] = {}
    rejected = 0
    for element in elements:
        try:
            event = _event(element, classes, area, now)
        except (ValueError, TypeError, KeyError, OverflowError):
            event = None
        if event is None:
            rejected += 1
        else:
            events[event.id] = event
    detail = f"{rejected} features excluded by location or validation. "
    if len(elements) == MAX_FEATURES:
        detail += "The feature bound was reached; more may exist. "
    return tuple(events.values()), detail


def _classify(tags: dict[str, Any], classes: tuple[FeatureClass, ...]) -> FeatureClass:
    """The first named class whose filters this feature's tags satisfy."""
    for feature in classes:
        for filters in feature.filters:
            if _matches(tags, filters):
                return feature
    raise ValueError("Feature matches none of the requested classes")


def _matches(tags: dict[str, Any], filters: str) -> bool:
    for clause in filters.strip("[]").split("]["):
        if "~" in clause:
            key, _, pattern = clause.partition("~")
            value = tags.get(key.strip('"'))
            if not isinstance(value, str) or not re.fullmatch(pattern.strip('"'), value):
                return False
        elif "=" in clause:
            key, _, expected = clause.partition("=")
            if tags.get(key.strip('"')) != expected.strip('"'):
                return False
        elif clause.strip('"') not in tags:
            return False
    return True


def _event(
    element: Any, classes: tuple[FeatureClass, ...], area: HazardArea, now: datetime
) -> Event | None:
    if not isinstance(element, dict):
        raise ValueError("Expected an Overpass element")
    kind, ident, tags = element.get("type"), element.get("id"), element.get("tags")
    if kind not in {"node", "way", "relation"} or type(ident) is not int or ident <= 0:
        raise ValueError("Invalid element identity")
    if not isinstance(tags, dict):
        return None
    centre = element if kind == "node" else element.get("center")
    if not isinstance(centre, dict):
        return None
    raw_lat, raw_lon = centre.get("lat"), centre.get("lon")
    if not isinstance(raw_lat, int | float) or not isinstance(raw_lon, int | float):
        return None
    lat, lon = float(raw_lat), float(raw_lon)
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    feature = _classify(tags, classes)
    geometry = area.intersecting_geometry(
        {"type": "Point", "coordinates": [lon, lat]}, SOURCE_ID, ORGANISATION
    )
    if geometry is None:
        return None
    name = tags.get("name:en") or tags.get("name")
    label = str(name)[:160] if isinstance(name, str) and name.strip() else "unnamed"
    kept = {key: str(tags[key])[:120] for key in _TAG_KEYS if isinstance(tags.get(key), str)}
    described = "; ".join(f"{key}={value}" for key, value in list(kept.items())[:_TAG_LIMIT])
    key = f"{kind}/{ident}"
    return Event(
        id=event_id(SOURCE_ID, key),
        source_id=SOURCE_ID,
        category=Category.NEWS,
        subtype="osm_feature",
        title=f"{feature.label}: {label}",
        summary=(
            f"OpenStreetMap {kind} {ident}, tagged as a {feature.label.lower()}, inside the "
            f"research area at {lat:.5f}, {lon:.5f}. Tags: {described or 'none kept'}. "
            "Current map state; the map does not date the feature."
        )[:2000],
        url=f"https://www.openstreetmap.org/{kind}/{ident}",
        published_at=None,
        observed_at=now,
        reliability=Reliability.C,
        credibility=Credibility.POSSIBLY_TRUE,
        grade_rationale=(
            "Volunteer-maintained map data; the feature's presence and name are community "
            "entries, not an observation of the scene."
        ),
        point=Point(lon=lon, lat=lat),
        geo_confidence=GeoConfidence.EXACT,
        tags=frozenset({"osm", feature.key}),
        geometry=geometry,
        attributes=freeze_attributes(
            {
                "osm_type": kind,
                "osm_id": ident,
                "feature_class": feature.key,
                "feature_label": feature.label,
                "tags": described,
                "licence": "ODbL 1.0, OpenStreetMap contributors",
            }
        ),
    )

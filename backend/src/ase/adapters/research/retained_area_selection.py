"""Bounded exact point selection over public feed snapshots, without copying events."""

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from shapely.geometry import Point as ShapePoint
from shapely.geometry import shape
from shapely.prepared import prep

from ase.domain.events import BoundingBox, Category, Event, GeoConfidence
from ase.domain.evidence_geometry import LocationRole
from ase.domain.evidence_time import evidence_matches_time
from ase.domain.research import ResearchQuery
from ase.domain.research_area import ResearchArea
from ase.domain.source_controls import source_control_keys

SCAN_PER_CATEGORY = 2000


class AreaPointFilter:
    def __init__(self, area: ResearchArea) -> None:
        geometry = shape(area.geometry.to_collection()["features"][0]["geometry"])
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError("Retained-feed area requires valid polygon topology")
        self.bounds = BoundingBox(*geometry.bounds)
        self._prepared = prep(geometry)

    def contains(self, event: Event) -> bool:
        point = event.point
        if point is None or event.geo_confidence is not GeoConfidence.EXACT:
            return False
        # Legacy EONET feed records label averaged polygon display centres EXACT
        # without retaining the original shape. They cannot establish membership
        # of a research area, even when that centre happens to fall inside it.
        if event.source_id == "nasa_eonet" and (
            event.geometry is None
            or event.geometry.source_id != event.source_id
            or event.geometry.location_role is not LocationRole.INCIDENT
        ):
            return False
        if event.geometry is not None:
            # A scene footprint, publisher's office or drawing must not acquire an
            # incident location from its representative map point.
            if event.geometry.location_role not in {
                LocationRole.INCIDENT,
                LocationRole.PROJECT_SITE,
            }:
                return False
            original = event.geometry.to_geometry()
            if original["type"] != "Point" or original["coordinates"] != [point.lon, point.lat]:
                return False
        # Covers includes the exact outer/hole boundary, but excludes hole interiors.
        # No buffer, rounding, polygon envelope substitution or inferred location.
        return bool(self._prepared.covers(ShapePoint(point.lon, point.lat)))


@dataclass(frozen=True, slots=True)
class AreaSnapshot:
    items: tuple[Event, ...]
    scanned: int
    excluded: int
    truncated: bool


def select_snapshot(
    events: Sequence[Event], spatial: AreaPointFilter, query: ResearchQuery
) -> AreaSnapshot:
    bounded = events[:SCAN_PER_CATEGORY]
    matches = tuple(
        event
        for event in bounded
        if spatial.contains(event)
        and evidence_matches_time(event, query.effective_time_basis, query.since, query.until)
        and (not query.country_isos or event.country_iso in query.country_isos)
    )
    return AreaSnapshot(
        matches, len(bounded), len(bounded) - len(matches), len(events) > SCAN_PER_CATEGORY
    )


def enabled_event(event: Event, disabled: frozenset[str], enabled: Mapping[str, bool]) -> bool:
    return not any(key in disabled for key in source_control_keys(event.source_id)) and enabled.get(
        event.source_id, False
    )


def fair_selection(events: Sequence[Event], per_category: int) -> tuple[Event, ...]:
    """Round-robin sources inside categories, then categories inside the result."""
    categories: dict[Category, dict[str, deque[Event]]] = defaultdict(lambda: defaultdict(deque))
    for event in events:
        categories[event.category][event.source_id].append(event)
    category_results: list[deque[Event]] = []
    for category in Category:
        sources = categories.get(category, {})
        queues = [sources[key] for key in sorted(sources)]
        chosen: deque[Event] = deque()
        while queues and len(chosen) < per_category:
            remaining = []
            for queue in queues:
                if len(chosen) == per_category:
                    break
                chosen.append(queue.popleft())
                if queue:
                    remaining.append(queue)
            queues = remaining
        if chosen:
            category_results.append(chosen)
    result: list[Event] = []
    while category_results:
        remaining_categories = []
        for queue in category_results:
            result.append(queue.popleft())
            if queue:
                remaining_categories.append(queue)
        category_results = remaining_categories
    return tuple(result)

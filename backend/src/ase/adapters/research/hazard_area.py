"""Shared bounded transport and exact geometry checks for fresh area hazard queries."""

import json
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from itertools import pairwise
from typing import Any

from shapely.geometry import shape
from shapely.prepared import prep

from ase.adapters.feeds.http import FeedHttpClient
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports import Clock
from ase.domain.events import Event
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchMode,
    ResearchQuery,
)
from ase.domain.research_area import ResearchArea

MAX_BODY_BYTES = 1024 * 1024
MAX_OBSERVATION_BYTES = 32 * 1024
MAX_OBSERVATION_VERTICES = 1024


def number(value: Any) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 50:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def supports(query: ResearchQuery) -> bool:
    return (
        query.area is not None
        and query.focus is ResearchFocus.GENERAL
        and not query.country_isos
        and query.effective_time_basis is EvidenceTimeBasis.RESEARCH
        and query.until - query.since <= timedelta(days=14)
    )


def page_limit(query: ResearchQuery) -> int:
    return 50 if query.mode is ResearchMode.QUICK else 100


class HazardArea:
    def __init__(self, area: ResearchArea) -> None:
        polygon = shape(area.geometry.to_collection()["features"][0]["geometry"])
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Unsupported area topology")
        self.bounds = tuple(float(value) for value in polygon.bounds)
        self._prepared = prep(polygon)

    def intersecting_geometry(
        self, raw: dict[str, Any], source_id: str, attribution: str
    ) -> EvidenceGeometry | None:
        kind = raw.get("type")
        if kind not in {"Point", "Polygon", "MultiPolygon"}:
            raise ValueError("Unsupported hazard geometry")
        text = json.dumps({"type": kind, "coordinates": raw.get("coordinates")}, allow_nan=False)
        if len(text.encode("utf-8")) > MAX_OBSERVATION_BYTES:
            raise ValueError("Hazard geometry exceeds admission bounds")
        geometry = EvidenceGeometry(
            text,
            LocationRole.INCIDENT if kind == "Point" else LocationRole.REPORTED_AREA,
            "source-reported point" if kind == "Point" else "source-reported event extent",
            "Exact local intersection of original WGS84 geometry; no inferred incident centre",
            source_id,
            attribution,
        )
        if geometry.vertices > MAX_OBSERVATION_VERTICES:
            raise ValueError("Hazard geometry exceeds vertex bounds")
        if kind != "Point":
            coordinates = geometry.to_geometry()["coordinates"]
            polygons = [coordinates] if kind == "Polygon" else coordinates
            if any(
                abs(a[0] - b[0]) > 180
                for polygon in polygons
                for ring in polygon
                for a, b in pairwise(ring)
            ):
                raise ValueError("Unsplit antimeridian geometry is ambiguous")
        candidate = shape(geometry.to_geometry())
        if candidate.is_empty or not candidate.is_valid:
            raise ValueError("Invalid source topology")
        return geometry if self._prepared.intersects(candidate) else None


def receipt(
    source_id: str,
    name: str,
    status: CollectionStatus,
    explanation: str,
    items: tuple[Event, ...] = (),
) -> ResearchBatch:
    return ResearchBatch(
        items, (CollectionAttempt(source_id, name, status, len(items), explanation[:1000]),)
    )


async def collect(
    http: FeedHttpClient,
    clock: Clock,
    query: ResearchQuery,
    source_id: str,
    name: str,
    description: str,
    url: Callable[[ResearchQuery, HazardArea], str],
    parse: Callable[[Any, ResearchQuery, HazardArea, datetime], tuple[tuple[Event, ...], str]],
) -> ResearchBatch:
    if not supports(query) or query.area is None:
        return receipt(source_id, name, CollectionStatus.UNSUPPORTED, description)
    try:
        area = await joined_thread_call(partial(HazardArea, query.area))
        # The shared SSRF-pinned client enforces its streaming cap (normally 5 MiB).
        # Only 1 MiB is admitted to JSON/geometry work; no pagination or retries.
        body = await http.get_bytes(url(query, area), conditional=False, max_redirects=0)
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("Hazard response exceeds admission byte limit")

        def project() -> tuple[tuple[Event, ...], str]:
            return parse(json.loads(body), query, area, clock.now())

        items, detail = await joined_thread_call(project)
    except TimeoutError:
        return receipt(source_id, name, CollectionStatus.TIMED_OUT, "The hazard request timed out.")
    except Exception:
        # Provider errors can include the operator's area; expose no error bodies or URLs.
        return receipt(
            source_id,
            name,
            CollectionStatus.FAILED,
            "Hazard data could not be retrieved or validated within its bounds. "
            "No coverage was established; no fallback request was made.",
        )
    return receipt(
        source_id,
        name,
        CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
        detail + " " + description,
        items,
    )

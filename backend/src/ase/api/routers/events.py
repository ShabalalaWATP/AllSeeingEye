"""Query the live event store."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.errors import InvalidQuery
from ase.api.schemas_events import EventOut, EventsOut, StoreStatsOut
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.feeds import EventQuery
from ase.domain.errors import NotFound
from ase.domain.events import BoundingBox, Category, Event
from ase.domain.evidence_time import EvidenceTimeBasis, MapTimeBasis

router = APIRouter(prefix="/events", tags=["events"])


def parse_categories(value: str | None) -> frozenset[Category]:
    if not value:
        return frozenset()
    try:
        return frozenset(Category(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise InvalidQuery(fields={"categories": "Unknown category"}) from exc


def parse_bbox(value: str | None) -> BoundingBox | None:
    if not value:
        return None
    try:
        west, south, east, north = (float(part) for part in value.split(","))
    except ValueError as exc:
        raise InvalidQuery(fields={"bbox": "Use west,south,east,north"}) from exc
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
        raise InvalidQuery(fields={"bbox": "Coordinates out of range"})
    return BoundingBox(west=west, south=south, east=east, north=north)


@router.get("")
async def list_events(
    user: CurrentUser,
    container: ContainerDep,
    claims: ClaimsDep,
    categories: Annotated[str | None, Query(max_length=200)] = None,
    bbox: Annotated[str | None, Query(max_length=120)] = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    since: datetime | None = None,
    sources: Annotated[str | None, Query(max_length=500)] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
    military: Annotated[
        bool | None,
        Query(
            description="Reported military aircraft/vessel classification; affiliation unverified."
        ),
    ] = None,
    offset: Annotated[int, Query(ge=0, le=15_000)] = 0,
    sampling: Literal["newest", "geographic"] = "newest",
    time_basis: Literal["publication", "map_record_time"] = "publication",
) -> EventsOut:
    query = EventQuery(
        categories=parse_categories(categories),
        bbox=parse_bbox(bbox),
        country_iso=country.upper() if country else None,
        since=since,
        source_ids=frozenset(s.strip() for s in sources.split(",") if s.strip())
        if sources
        else frozenset(),
        limit=limit,
        military=military,
        offset=offset,
        sampling=sampling,
        time_basis=MapTimeBasis.MAP
        if time_basis == "map_record_time"
        else EvidenceTimeBasis.PUBLICATION,
    )
    container.map_interests.request(user.id, query)

    def project(events: list[Event]) -> EventsOut:
        items = [EventOut.from_event(event) for event in events]
        return EventsOut(items=items, count=len(items))

    result = (
        await container.store.read_cooperatively(query, project, admission_key=f"user:{user.id}")
        if isinstance(container.store, CooperativeEventReader)
        else project(container.store.query(query))
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    return result


@router.get("/stats")
async def store_stats(user: CurrentUser, container: ContainerDep) -> StoreStatsOut:
    return StoreStatsOut.from_stats(container.store.stats())


@router.get("/{event_id}")
async def get_event(event_id: str, user: CurrentUser, container: ContainerDep) -> EventOut:
    event = container.store.get(event_id)
    if event is None:
        raise NotFound()
    return EventOut.from_event(event)

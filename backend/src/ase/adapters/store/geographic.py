"""Deterministic spatial diversity of already-filtered live records, not statistical sampling."""

from collections import deque
from collections.abc import Sequence
from math import floor

from ase.domain.events import Category, Event
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_order

CELL_DEGREES = 10


def geographic_page(
    events: Sequence[Event], basis: EvidenceTimeBasis, offset: int, limit: int
) -> list[Event]:
    """Round-robin cells, then categories per cell, then newest records per category.

    Cells and their categories are ordered by their newest (time, ID) record.
    A cell has only one turn per round regardless of its number of categories.
    Unlocated records form
    one final bucket per round; they neither acquire coordinates nor crowd out
    the first located record. Equal-angle cells do not imply equal surface area.
    Pagination is repeatable for an unchanged store and query, not a snapshot
    guarantee across concurrent live updates.
    """
    cells: dict[tuple[int, int], dict[Category, deque[Event]]] = {}
    unlocated: dict[Category, deque[Event]] = {}
    for event in sorted(events, key=lambda e: (evidence_order(e, basis), e.id), reverse=True):
        if event.point is None:
            unlocated.setdefault(event.category, deque()).append(event)
            continue
        # Both representations of the antimeridian belong to the same cell;
        # the north pole remains in the final valid latitude band.
        longitude = (event.point.lon + 180) % 360
        latitude = min(17, floor((event.point.lat + 90) / CELL_DEGREES))
        key = (floor(longitude / CELL_DEGREES), latitude)
        cells.setdefault(key, {}).setdefault(event.category, deque()).append(event)
    active = deque(deque(categories.values()) for categories in cells.values())
    if unlocated:
        active.append(deque(unlocated.values()))
    result: list[Event] = []
    position = 0
    while active and len(result) < limit:
        categories = active.popleft()
        bucket = categories.popleft()
        event = bucket.popleft()
        if position >= offset:
            result.append(event)
        position += 1
        if bucket:
            categories.append(bucket)
        if categories:
            active.append(categories)
    return result

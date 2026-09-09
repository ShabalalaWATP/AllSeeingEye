"""Deterministic spatial diversity of already-filtered live records, not statistical sampling."""

from collections import deque
from collections.abc import Sequence
from datetime import datetime
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
    cells: dict[tuple[int, int], dict[Category, list[Event]]] = {}
    unlocated: dict[Category, list[Event]] = {}
    for event in events:
        if event.point is None:
            unlocated.setdefault(event.category, []).append(event)
            continue
        # Both representations of the antimeridian belong to the same cell;
        # the north pole remains in the final valid latitude band.
        longitude = (event.point.lon + 180) % 360
        latitude = min(17, floor((event.point.lat + 90) / CELL_DEGREES))
        key = (floor(longitude / CELL_DEGREES), latitude)
        cells.setdefault(key, {}).setdefault(event.category, []).append(event)

    # Sort within spatial buckets, then only their heads globally. This preserves
    # the same newest-first round robin without a large global comparison sort.
    def rank(event: Event) -> tuple[datetime, str]:
        return evidence_order(event, basis), event.id

    def ordered_categories(categories: dict[Category, list[Event]]) -> deque[deque[Event]]:
        buckets = [deque(sorted(bucket, key=rank, reverse=True)) for bucket in categories.values()]
        return deque(sorted(buckets, key=lambda bucket: rank(bucket[0]), reverse=True))

    grouped = [ordered_categories(categories) for categories in cells.values()]
    active = deque(sorted(grouped, key=lambda buckets: rank(buckets[0][0]), reverse=True))
    if unlocated:
        active.append(ordered_categories(unlocated))
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

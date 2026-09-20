"""Pure filtering and ranking over an immutable retained-event snapshot."""

from collections.abc import Sequence
from heapq import nlargest

from ase.adapters.store.geographic import geographic_page
from ase.application.ports.feeds import EventQuery
from ase.domain.area_membership import area_contains_event
from ase.domain.events import Event
from ase.domain.evidence_time import evidence_matches_time, evidence_order
from ase.domain.traffic_classification import is_reported_military


def select_events(candidates: Sequence[Event], query: EventQuery) -> list[Event]:
    matched: list[Event] = []
    for event in candidates:
        if query.source_ids and event.source_id not in query.source_ids:
            continue
        if query.military is not None and is_reported_military(event) is not query.military:
            continue
        if not evidence_matches_time(
            event,
            query.time_basis,
            query.since,
            query.until,
            include_unknown=query.include_unknown_dates,
        ):
            continue
        if query.bbox is not None and (event.point is None or not query.bbox.contains(event.point)):
            continue
        if query.research_area is not None and not area_contains_event(query.research_area, event):
            continue
        matched.append(event)
    offset = max(0, min(15_000, query.offset))
    if query.sampling == "geographic":
        return geographic_page(matched, query.time_basis, offset, max(1, query.limit))
    ranked = nlargest(
        offset + max(1, query.limit),
        matched,
        key=lambda e: (evidence_order(e, query.time_basis), e.id),
    )
    return ranked[offset:]

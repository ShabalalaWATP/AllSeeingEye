"""Append relevant fresh challenge records without relabelling packet v1."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ase.application.reports.selection import Selection, term_matches
from ase.domain.events import Event
from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.grading import SourceProfile
from ase.domain.research import ResearchBatch, ResearchMode
from ase.domain.source_ratings import unassessed_source_rating

FINAL_LIMITS = {ResearchMode.QUICK: 24, ResearchMode.DETAILED: 48, ResearchMode.ADVANCED: 80}
ADDITION_LIMITS = {ResearchMode.QUICK: 0, ResearchMode.DETAILED: 8, ResearchMode.ADVANCED: 12}


def append_challenge_evidence(
    initial: Selection,
    batch: ResearchBatch,
    profiles: Mapping[str, SourceProfile],
    *,
    terms: tuple[str, ...],
    mode: ResearchMode,
    now: datetime,
) -> tuple[Selection, tuple[EvidenceItem, ...]]:
    """Only original provider records can enter v2; generated reviews remain context."""
    maximum = min(ADDITION_LIMITS[mode], FINAL_LIMITS[mode] - len(initial.items))
    if maximum <= 0:
        return initial, ()
    existing_ids = {row.event_id for row in initial.items}
    existing_hashes = {row.content_hash for row in initial.items if row.content_hash}
    labels = {row.label for row in initial.items}
    next_label = max((int(label[1:]) for label in labels if label[1:].isdigit()), default=0) + 1
    safe: list[Event] = []
    flagged = 0
    for event in batch.items:
        if injection_flags(event.title, event.title_en, event.summary):
            flagged += 1
        elif (
            event.id not in existing_ids
            and (not event.content_hash or event.content_hash not in existing_hashes)
            and term_matches(event, terms)
        ):
            safe.append(event)
    safe.sort(key=lambda event: (-term_matches(event, terms), event.id))
    added: list[EvidenceItem] = []
    for event in safe:
        if len(added) >= maximum:
            break
        profile = profiles.get(event.source_id)
        added.append(
            EvidenceItem.from_event(
                f"E{next_label + len(added)}",
                event,
                now,
                source_name=profile.name if profile else event.source_id,
                independence_key=profile.independence_key if profile else "",
                instrument=profile.instrument if profile else False,
                source_rating=profile.rating if profile else unassessed_source_rating(),
                flags=sorted(
                    (profile.flags if profile else frozenset())
                    | event.tags & {"state_controlled", "interested_party"}
                ),
            )
        )
    return (
        Selection(
            (*initial.items, *added),
            initial.flagged + flagged,
            initial.considered + len(batch.items),
        ),
        tuple(added),
    )

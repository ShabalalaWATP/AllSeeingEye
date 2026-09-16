"""Diversity, duplicate folding and the final evidence slots inside the strategy caps."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from ase.application.reports.templates import EvidenceStrategy
from ase.domain.events import Event
from ase.domain.evidence import CorroborationMember, EvidenceItem
from ase.domain.evidence_clusters import MAX_CORROBORATION_MEMBERS
from ase.domain.grading import SourceProfile
from ase.domain.source_ratings import unassessed_source_rating


@dataclass(frozen=True, slots=True)
class Chosen:
    items: tuple[EvidenceItem, ...]
    merged: int


def organisation_of(event: Event, profiles: Mapping[str, SourceProfile]) -> tuple[str, str]:
    profile = profiles.get(event.source_id)
    if profile is not None and profile.independence_key:
        return ("organisation", profile.independence_key)
    return ("connector", event.source_id)


def term_presence(event: Event, terms: Sequence[str]) -> int:
    """Match original and translated titles without replacing the source material."""
    if not terms:
        return 0
    text = f"{event.title} {event.title_en or ''} {event.summary or ''}".lower()
    return sum(1 for term in terms if term in text)


def diversify(
    ranked: Sequence[Event], profiles: Mapping[str, SourceProfile], terms: Sequence[str]
) -> list[Event]:
    """Prefer varied reporting, then backfill without discarding possible counterevidence.

    Matching evidence stays ahead of unmatched context. Within either tier, the first
    pass takes one item per declared organisation and defers equal titles or hashes.
    This is a bounded retrieval heuristic, not proof of independent sourcing. Deferred
    items remain available when the pool is thin, including similar opposing reports.
    """
    result: list[Event] = []
    for matching in (True, False):
        organisations: set[tuple[str, str]] = set()
        titles: set[str] = set()
        hashes: set[str] = set()
        deferred: list[Event] = []
        for event in ranked:
            if bool(term_presence(event, terms)) != matching:
                continue
            organisation = organisation_of(event, profiles)
            title = " ".join((event.title_en or event.title).casefold().split())
            copied = (bool(title) and title in titles) or (
                bool(event.content_hash) and event.content_hash in hashes
            )
            if organisation in organisations or copied:
                deferred.append(event)
                continue
            organisations.add(organisation)
            if title:
                titles.add(title)
            if event.content_hash:
                hashes.add(event.content_hash)
            result.append(event)
        result.extend(deferred)
    return result


def _member(
    event: Event, profiles: Mapping[str, SourceProfile], reasons: tuple[str, ...]
) -> CorroborationMember:
    profile = profiles.get(event.source_id)
    return CorroborationMember(
        event_id=event.id,
        source_id=event.source_id,
        source_name=profile.name if profile else event.source_id,
        independence_key=profile.independence_key if profile else "",
        title=event.title_en or event.title,
        url=event.url,
        published_at=event.published_at,
        reasons=reasons,
    )


def _item(
    label: str, event: Event, now: datetime, profiles: Mapping[str, SourceProfile]
) -> EvidenceItem:
    profile = profiles.get(event.source_id)
    return EvidenceItem.from_event(
        label,
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


def choose_items(
    ranked: Sequence[Event],
    profiles: Mapping[str, SourceProfile],
    strategy: EvidenceStrategy,
    *,
    now: datetime,
    clusters: Mapping[str, str],
    cluster_reasons: Mapping[str, tuple[str, ...]],
) -> Chosen:
    """Give each duplicate cluster one slot and attach the folded copies to it.

    The representative is the highest-ranked member, so ranking still decides what the
    model reads. Folded copies never consume a slot and never add an organisation to
    the per-organisation cap: repeated text is one piece of reporting, not several.
    """
    per_organisation: dict[tuple[str, str], int] = {}
    chosen: list[EvidenceItem] = []
    representative: dict[str, int] = {}
    folded: dict[int, list[CorroborationMember]] = {}
    merged = 0
    for event in ranked:
        key = clusters.get(event.id, event.id)
        index = representative.get(key)
        if index is not None:
            merged += 1
            members = folded.setdefault(index, [])
            if len(members) < MAX_CORROBORATION_MEMBERS:
                members.append(_member(event, profiles, cluster_reasons.get(key, ())))
            continue
        if len(chosen) >= strategy.max_items:
            continue
        organisation = organisation_of(event, profiles)
        if per_organisation.get(organisation, 0) >= strategy.per_source_cap:
            continue
        per_organisation[organisation] = per_organisation.get(organisation, 0) + 1
        representative[key] = len(chosen)
        chosen.append(_item(f"E{len(chosen) + 1}", event, now, profiles))
    return Chosen(
        tuple(
            replace(item, corroboration=tuple(folded[index])) if index in folded else item
            for index, item in enumerate(chosen)
        ),
        merged,
    )

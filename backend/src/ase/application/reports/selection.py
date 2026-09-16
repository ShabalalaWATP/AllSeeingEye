"""Evidence selection: a deterministic prefilter, an optional rerank, then diversity.

Stage one is the explainable filter of docs/03 section 9: scope, period, category and
term groups. Stage two may reorder the survivors by embedding similarity to the
question and its intelligence requirements. Stage three folds duplicates and spends
the slots, keeping the per-organisation cap and the retained opposing reporting.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ase.application.ports.feeds import EventStore
from ase.application.reports.selection_choice import choose_items, diversify, term_presence
from ase.application.reports.selection_pool import (
    CREDIBILITY_WEIGHT,
    MAX_POOL,
    RELIABILITY_WEIGHT,
    candidate_pool,
    score,
)
from ase.application.reports.subscription_updates import content_signature
from ase.application.reports.templates import EvidenceStrategy
from ase.domain.events import BoundingBox, Category, Event
from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.evidence_clusters import duplicate_clusters
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.grading import SourceProfile
from ase.domain.project import project_to_dict
from ase.domain.trackers import Hazard, hazard_of

__all__ = [
    "CREDIBILITY_WEIGHT",
    "MAX_POOL",
    "MAX_RERANK_CANDIDATES",
    "RELIABILITY_WEIGHT",
    "RERANK_WEIGHT",
    "Selection",
    "SelectionPlan",
    "finish_selection",
    "plan_selection",
    "score",
    "select_evidence",
    "term_matches",
]

# A bounded rerank: one embedding request covers the question and these survivors.
MAX_RERANK_CANDIDATES = 120
# Similarity reweights the deterministic priority; it never replaces grade or recency.
RERANK_WEIGHT = 1.0


@dataclass(frozen=True, slots=True)
class Selection:
    items: tuple[EvidenceItem, ...]
    flagged: int
    considered: int
    merged: int = 0
    reranked: int = 0
    rerank_reason: str = ""


def term_matches(event: Event, terms: Sequence[str]) -> int:
    """Match original and translated titles without replacing the source material."""
    return term_presence(event, terms)


@dataclass(frozen=True, slots=True)
class SelectionPlan:
    """The deterministic survivors, before any similarity ordering is applied."""

    safe: tuple[Event, ...]
    considered: int
    term_groups: tuple[tuple[str, ...], ...]
    strategy: EvidenceStrategy
    now: datetime
    reference: datetime
    window: timedelta
    time_basis: EvidenceTimeBasis
    seen_content_signatures: frozenset[str] = frozenset()
    group_index: Mapping[str, int] = field(default_factory=dict)

    @property
    def flagged(self) -> int:
        return self.considered - len(self.safe)

    @property
    def terms(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(term for group in self.term_groups for term in group))

    def priority(self, event: Event, similarity: Mapping[str, float] | None = None) -> float:
        group = self.group_index[event.id]
        matches = (
            term_matches(event, self.term_groups[group]) if group < len(self.term_groups) else 0
        )
        nearness = max(0.0, (similarity or {}).get(event.id, 0.0))
        return (
            score(event, self.reference, self.window, self.time_basis)
            * (1 + 0.25 * matches)
            * (1 + RERANK_WEIGHT * nearness)
        )

    def rerank_candidates(self, limit: int = MAX_RERANK_CANDIDATES) -> tuple[Event, ...]:
        """The highest-priority survivors, so one bounded embedding call can rank them."""
        ordered = sorted(
            self.safe,
            key=lambda event: (self.group_index[event.id], -self.priority(event), event.id),
        )
        return tuple(ordered[: max(0, limit)])


def plan_selection(
    store: EventStore,
    strategy: EvidenceStrategy,
    *,
    now: datetime,
    country_iso: str | None = None,
    categories: Sequence[Category] = (),
    terms: Sequence[str] = (),
    term_groups: Sequence[Sequence[str]] = (),
    bbox: BoundingBox | None = None,
    countries: Sequence[str] = (),
    hazard: Hazard | None = None,
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION,
    until: datetime | None = None,
    since: datetime | None = None,
    include_unknown_dates: bool = False,
    include_country_subjects: bool = False,
    seen_content_signatures: frozenset[str] = frozenset(),
) -> SelectionPlan:
    """The deterministic prefilter: scope, period, category, terms and injection safety."""
    window = (
        (until - since)
        if since is not None and until is not None
        else timedelta(hours=strategy.window_hours)
    )
    pool = candidate_pool(
        store,
        frozenset(categories) or strategy.categories,
        since if since is not None else now - window,
        country_iso,
        bbox,
        countries,
        time_basis,
        until,
        include_unknown_dates,
        include_country_subjects,
    )
    if hazard is not None:
        pool = [event for event in pool if hazard_of(event) is hazard]
    lowered_groups = tuple(
        tuple(term.lower().strip() for term in group if term.strip())
        for group in (term_groups or (terms,))
    )
    safe = [
        event
        for event in pool
        if not injection_flags(
            event.title,
            event.title_en,
            event.summary,
            *(value for value in project_to_dict(event.project).values() if isinstance(value, str))
            if event.project is not None
            else (),
        )
    ]
    group_index = {
        event.id: next(
            (index for index, group in enumerate(lowered_groups) if term_matches(event, group)),
            len(lowered_groups),
        )
        for event in safe
    }
    return SelectionPlan(
        safe=tuple(safe),
        considered=len(pool),
        term_groups=lowered_groups,
        strategy=strategy,
        now=now,
        reference=until if since is not None and until is not None else now,
        window=window,
        time_basis=time_basis,
        seen_content_signatures=seen_content_signatures,
        group_index=group_index,
    )


def finish_selection(
    plan: SelectionPlan,
    profiles: Mapping[str, SourceProfile],
    *,
    similarity: Mapping[str, float] | None = None,
    rerank_reason: str = "",
) -> Selection:
    """Order, diversify, fold duplicates and spend the slots inside the strategy caps.

    Earlier term groups still take precedence, so a rerank reorders inside a relevance
    tier and never promotes unmatched context above matched reporting. Diversity, the
    per-organisation cap and the retained opposing reporting are unchanged.
    """
    ordered = sorted(
        plan.safe,
        key=lambda event: (
            plan.group_index[event.id],
            -plan.priority(event, similarity),
            event.id,
        ),
    )
    buckets: list[list[Event]] = [[] for _ in range(len(plan.term_groups) + 1)]
    for event in ordered:
        buckets[plan.group_index[event.id]].append(event)
    ranked = [event for bucket in buckets for event in diversify(bucket, profiles, plan.terms)]
    if plan.seen_content_signatures:
        # Preserve relevance ahead of novelty, and quality/diversity within each group.
        # Repeated items may still supply essential context after new relevant evidence.
        ranked.sort(
            key=lambda event: (
                plan.group_index[event.id],
                content_signature(event) in plan.seen_content_signatures,
            )
        )
    clusters, cluster_reasons = duplicate_clusters(plan.safe)
    chosen = choose_items(
        ranked,
        profiles,
        plan.strategy,
        now=plan.now,
        clusters=clusters,
        cluster_reasons=cluster_reasons,
    )
    scored = sum(1 for event in plan.safe if event.id in (similarity or {}))
    return Selection(
        items=chosen.items,
        flagged=plan.flagged,
        considered=plan.considered,
        merged=chosen.merged,
        reranked=scored,
        rerank_reason=rerank_reason,
    )


def select_evidence(
    store: EventStore,
    profiles: Mapping[str, SourceProfile],
    strategy: EvidenceStrategy,
    *,
    now: datetime,
    country_iso: str | None = None,
    categories: Sequence[Category] = (),
    terms: Sequence[str] = (),
    term_groups: Sequence[Sequence[str]] = (),
    bbox: BoundingBox | None = None,
    countries: Sequence[str] = (),
    hazard: Hazard | None = None,
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION,
    until: datetime | None = None,
    since: datetime | None = None,
    include_unknown_dates: bool = False,
    include_country_subjects: bool = False,
    seen_content_signatures: frozenset[str] = frozenset(),
    similarity: Mapping[str, float] | None = None,
    rerank_reason: str = "",
) -> Selection:
    """Freeze the best evidence for the scope; items with instruction-like text are left out.

    A bounding box and extra countries widen the pool (a conflict area); a hazard
    narrows it to one kind of disaster. Without a similarity map the ordering is
    exactly the deterministic grade, recency and term ordering.
    """
    plan = plan_selection(
        store,
        strategy,
        now=now,
        country_iso=country_iso,
        categories=categories,
        terms=terms,
        term_groups=term_groups,
        bbox=bbox,
        countries=countries,
        hazard=hazard,
        time_basis=time_basis,
        until=until,
        since=since,
        include_unknown_dates=include_unknown_dates,
        include_country_subjects=include_country_subjects,
        seen_content_signatures=seen_content_signatures,
    )
    return finish_selection(plan, profiles, similarity=similarity, rerank_reason=rerank_reason)

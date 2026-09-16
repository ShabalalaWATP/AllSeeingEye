"""Scope selection for public reporting versus explicitly supplied private inputs."""

from collections.abc import Mapping
from dataclasses import replace

from ase.application.ports.feeds import EventStore
from ase.application.reports.depth import depth_for
from ase.application.reports.production_types import Job
from ase.application.reports.reused_evidence import with_reused_evidence
from ase.application.reports.selection import (
    Selection,
    SelectionPlan,
    finish_selection,
    plan_selection,
)
from ase.application.reports.subscription_updates import previous_signatures
from ase.domain.direction import Direction
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.grading import SourceProfile
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchQuery
from ase.domain.research_records import ResearchReceipt


def _admitted_task_groups(receipt: ResearchReceipt | None) -> tuple[tuple[str, ...], ...]:
    if receipt is None:
        return ()
    passes = (
        ((row.plan, row.attempts) for row in receipt.passes)
        if receipt.passes
        else ((receipt.plan, receipt.attempts),)
    )
    groups: list[tuple[str, ...]] = []
    for plan, attempts in passes:
        if plan is None:
            continue
        completed = {
            attempt.task_id
            for attempt in attempts
            if attempt.status is CollectionStatus.COMPLETED and attempt.result_count > 0
        }
        groups.extend(
            task.terms
            for task in plan.tasks
            if task.purpose != "baseline"
            and task.selected
            and task.supported
            and task.task_id in completed
            and task.terms
        )
    return tuple(dict.fromkeys(groups))


def _term_groups(
    job: Job,
    direction: Direction | None,
    runtime_query: ResearchQuery | None,
    receipt: ResearchReceipt | None,
    extra_terms: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    if runtime_query is not None:
        # An admitted revision is the active baseline; keep the operator's exact
        # terms separately so a translation or revision cannot erase their priority.
        base = [runtime_query.terms]
        if job.request.research_terms is not None:
            base.append(job.request.research_terms)
        base.extend(variant.terms for variant in runtime_query.query_variants)
        base.extend(_admitted_task_groups(receipt))
    elif job.request.research_terms is not None:
        base = [job.request.research_terms]
        base.extend(variant.terms for variant in job.request.research_query_variants)
    elif direction is not None:
        base = [direction.search_terms]
    else:
        base = [job.terms]
    if extra_terms:
        base.append(extra_terms)
    return tuple(dict.fromkeys(group for group in base if group))


def plan_for_job(
    store: EventStore,
    job: Job,
    direction: Direction | None,
    extra_terms: tuple[str, ...] = (),
    *,
    runtime_query: ResearchQuery | None = None,
    receipt: ResearchReceipt | None = None,
    reserve_challenge_slots: bool = False,
) -> SelectionPlan:
    """The deterministic prefilter for this job, before any similarity ordering."""
    private = job.request.research_focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA)
    area = job.request.effective_area is not None
    window = int(job.window.total_seconds() // 3600)
    if private and job.seed_events:
        # A supplied historic document is relevant because it was explicitly supplied,
        # not because its publication date fits a current news window. Preserve its date.
        dates = [item.published_at for item in job.seed_events if item.published_at is not None]
        if dates:
            earliest = min(dates)
            window = max(window, int((job.now - earliest).total_seconds() // 3600) + 1)
    strategy = replace(
        job.template.strategy,
        window_hours=window,
        categories=frozenset() if private else job.template.strategy.categories,
    )
    depth = depth_for(job.request.research_mode)
    if depth is not None:
        strategy = replace(
            strategy, max_items=depth.evidence_items, per_source_cap=depth.per_source_cap
        )
        if reserve_challenge_slots and job.request.research_mode is not None:
            reserved = {"quick": 0, "detailed": 8, "advanced": 12}[job.request.research_mode.value]
            strategy = replace(strategy, max_items=strategy.max_items - reserved)
    if private:
        # Private sections are parts of one supplied input, not competing publishers.
        # A diversity cap would discard later photographs, contradictions and caveats.
        # Preserve the complete bounded assessment within the report's 100-item ceiling;
        # original grades and the lack of independent corroboration remain unchanged.
        strategy = replace(strategy, max_items=100, per_source_cap=100)
    groups = _term_groups(job, direction, runtime_query, receipt, extra_terms)
    return plan_selection(
        store,
        strategy,
        now=job.now,
        country_iso=None if private else job.request.country_iso,
        categories=() if private else job.request.categories,
        term_groups=groups,
        # Area eligibility was admitted by spatial providers. A point-only filter
        # here would silently discard valid footprints without event coordinates.
        bbox=None if private or area else job.bbox,
        countries=()
        if private
        else tuple(dict.fromkeys((*job.request.country_isos, *job.countries))),
        hazard=None if private else job.hazard,
        time_basis=job.request.effective_time_basis,
        since=job.period_from if job.request.research_since is not None else None,
        until=job.period_to if job.request.research_until is not None else None,
        include_unknown_dates=private,
        include_country_subjects=(
            job.request.research_mode is not None
            and job.request.research_focus is ResearchFocus.GENERAL
            and not area
            and job.bbox is None
            and not job.countries
            and bool(job.request.country_isos)
            and job.request.effective_time_basis is not EvidenceTimeBasis.RECORDED
        ),
        seen_content_signatures=(
            previous_signatures(job.subscription_baseline)
            | frozenset(job.request.subscription_seen_signatures)
        ),
    )


def select_for_job(
    store: EventStore,
    profiles: Mapping[str, SourceProfile],
    job: Job,
    direction: Direction | None,
    extra_terms: tuple[str, ...] = (),
    *,
    runtime_query: ResearchQuery | None = None,
    receipt: ResearchReceipt | None = None,
    reserve_challenge_slots: bool = False,
    similarity: Mapping[str, float] | None = None,
    rerank_reason: str = "",
) -> Selection:
    """Freeze this job's evidence, optionally reordered by the supplied similarity map."""
    plan = plan_for_job(
        store,
        job,
        direction,
        extra_terms,
        runtime_query=runtime_query,
        receipt=receipt,
        reserve_challenge_slots=reserve_challenge_slots,
    )
    selected = finish_selection(plan, profiles, similarity=similarity, rerank_reason=rerank_reason)
    return with_reused_evidence(selected, job.reused_evidence)

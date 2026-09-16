"""Run the optional embedding rerank for one job and account for its single call."""

from __future__ import annotations

from ase.application.ports.feeds import EventStore
from ase.application.reports.evidence_rerank import EvidenceReranker, RerankOutcome
from ase.application.reports.production_selection import plan_for_job
from ase.application.reports.production_types import Job, Totals
from ase.domain.direction import Direction
from ase.domain.direction_requirements import effective_requirements
from ase.domain.research import ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_records import ResearchReceipt


def requirements_for_rerank(
    job: Job, direction: Direction | None
) -> tuple[IntelligenceRequirement, ...]:
    """Brief requirements when pinned, otherwise the direction call's derived PIR/SIR/EEIs."""
    return effective_requirements(job.request.canonical_requirements, direction)


async def rerank_for_job(
    reranker: EvidenceReranker | None,
    job: Job,
    store: EventStore,
    direction: Direction | None,
    query: ResearchQuery | None,
    receipt: ResearchReceipt | None,
    totals: Totals,
    *,
    resumed: bool,
) -> RerankOutcome:
    """Reorder the survivors when embeddings exist; otherwise leave today's order alone.

    A resumed job keeps its frozen selection, so it never pays for a second call.
    """
    if reranker is None or resumed:
        return RerankOutcome()
    plan = plan_for_job(store, job, direction, runtime_query=query, receipt=receipt)
    outcome = await reranker.rank(
        plan,
        question=job.request.question or job.title,
        requirements=requirements_for_rerank(job, direction),
        actor_id=job.actor.id,
        team_id=job.request.team_id,
        at=job.now,
    )
    if outcome.usage is not None:
        totals.usage.append(outcome.usage)
        totals.add(outcome.usage.prompt_tokens, 0, outcome.usage.latency_ms, ())
    return outcome

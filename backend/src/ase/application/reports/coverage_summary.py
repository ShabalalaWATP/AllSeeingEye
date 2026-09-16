"""Turn the frozen collection receipt and the selection into the coverage counts."""

from __future__ import annotations

from ase.application.reports.evidence_rerank import NO_CANDIDATES
from ase.application.reports.selection import Selection
from ase.domain.evidence_coverage import (
    RERANK_APPLIED,
    RERANK_NOT_ATTEMPTED,
    EvidenceCoverage,
    source_counts,
)
from ase.domain.research import CollectionStatus
from ase.domain.research_records import ResearchReceipt

# A source answered, answered with nothing, or did not answer. Everything else is
# "unavailable": unsupported, failed, timed out, not collected or budget exhausted.
_READ = CollectionStatus.COMPLETED
_EMPTY = CollectionStatus.EMPTY


def _attempt_statuses(receipt: ResearchReceipt) -> list[str]:
    attempts = [*receipt.attempts, *(row for pass_ in receipt.passes for row in pass_.attempts)]
    latest: dict[str, str] = {}
    for attempt in attempts:
        if attempt.status is _READ and attempt.result_count > 0:
            status = "read"
        elif attempt.status in (_READ, _EMPTY):
            status = "empty"
        else:
            status = "unavailable"
        # One source may be attempted more than once; its best outcome is its outcome.
        rank = {"read": 2, "empty": 1, "unavailable": 0}
        if rank[status] >= rank.get(latest.get(attempt.source_id, "unavailable"), 0):
            latest[attempt.source_id] = status
    return list(latest.values())


def _planned_sources(receipt: ResearchReceipt) -> int:
    plans = [receipt.plan, *(row.plan for row in receipt.passes)]
    return len({task.source_id for plan in plans if plan is not None for task in plan.tasks})


def coverage_for(selection: Selection, receipt: ResearchReceipt | None) -> EvidenceCoverage:
    """Every number comes from a recorded receipt or the selection; none is estimated."""
    statuses = _attempt_statuses(receipt) if receipt is not None else []
    read, empty, unavailable, not_attempted, considered = source_counts(
        statuses, _planned_sources(receipt) if receipt is not None else 0
    )
    if selection.rerank_reason and selection.rerank_reason != NO_CANDIDATES:
        status = selection.rerank_reason
    else:
        status = RERANK_APPLIED if selection.reranked else RERANK_NOT_ATTEMPTED
    return EvidenceCoverage(
        sources_considered=considered,
        sources_read=read,
        sources_empty=empty,
        sources_unavailable=unavailable,
        sources_not_attempted=not_attempted,
        items_retrieved=receipt.collected_items if receipt is not None else 0,
        items_considered=selection.considered,
        items_selected=len(selection.items),
        duplicates_merged=selection.merged,
        items_flagged=selection.flagged,
        reranked_candidates=selection.reranked,
        rerank_status=status,
    )

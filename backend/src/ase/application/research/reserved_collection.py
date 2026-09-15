"""Reserve and settle one checkpointed initial source request around outbound work."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from math import ceil

from ase.application.ports.research import (
    CheckpointedChallengeItems,
    ResearchProvider,
    SourceOperationCheckpoints,
)
from ase.application.research.phase_ledger import Phase
from ase.domain.events import Event
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_time import evidence_matches_time, evidence_time
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.research_plan import ResearchTask

CURRENT_RECORDS = frozenset(
    {
        "current_dns_snapshot",
        "current_registry_snapshot",
        "current_directory_snapshot",
        "current_certificate_snapshot",
    }
)
Fetch = Callable[[ResearchProvider, ResearchQuery, float], Awaitable[ResearchBatch]]
Freeze = Callable[[ResearchBatch], Awaitable[tuple[EvidenceItem, ...]]]


@dataclass(frozen=True, slots=True)
class ReservedFetch:
    batch: ResearchBatch | None
    accepted_keys: frozenset[str]
    status: CollectionStatus
    explanation: str


def source_item_key(event_id: str) -> str:
    """Keep arbitrary provider IDs out of the bounded durable ledger."""
    return hashlib.sha256(event_id.encode("utf-8")).hexdigest()


def eligible_for_query(item: Event, query: ResearchQuery) -> bool:
    timestamp = evidence_time(item, query.effective_time_basis)
    current_context = query.area is None and item.attributes.get("record_kind") in CURRENT_RECORDS
    return (current_context and timestamp is not None) or evidence_matches_time(
        item, query.effective_time_basis, query.since, query.until
    )


def _request_key(pass_index: int, task: ResearchTask, phase: Phase) -> str:
    if type(pass_index) is not int or pass_index not in (1, 2) or task.task_id is None:
        raise ValueError("A frozen source task and bounded pass are required")
    digest = hashlib.sha256(task.task_id.encode("utf-8")).hexdigest()
    return f"pass:{pass_index}:{digest}" if phase == "initial" else f"challenge:{digest}"


async def fetch_reserved(
    provider: ResearchProvider,
    task: ResearchTask,
    routed: ResearchQuery,
    query: ResearchQuery,
    seconds: float,
    *,
    max_items: int,
    seen_ids: frozenset[str],
    source_operations: SourceOperationCheckpoints,
    pass_index: int,
    phase: Phase = "initial",
    fetch: Fetch,
    freeze: Freeze | None = None,
) -> ReservedFetch:
    """A durable reservation must commit before dispatch; unknown results never replay."""
    key = _request_key(pass_index, task, phase)
    decision = await source_operations.reserve_source_operation(
        mode=query.mode, phase=phase, request_key=key
    )
    if not decision.dispatch:
        denied = decision.status == "denied"
        return ReservedFetch(
            None,
            frozenset(),
            CollectionStatus.BUDGET_EXHAUSTED if denied else CollectionStatus.NOT_COLLECTED,
            "The frozen source-phase allowance was reached before dispatch."
            if denied
            else "An earlier source operation cannot be replayed after interruption; "
            "its evidence was not checkpointed.",
        )
    if decision.status != "open" or decision.allowance_ms <= 0:
        raise ValueError("Invalid durable source reservation")
    clock = asyncio.get_running_loop().time
    started = clock()
    batch = await fetch(provider, routed, min(seconds, decision.allowance_ms / 1_000))
    elapsed_ms = min(decision.allowance_ms, max(0, ceil((clock() - started) * 1_000)))
    succeeded = not batch.attempts or batch.attempts[0].status in {
        CollectionStatus.COMPLETED,
        CollectionStatus.EMPTY,
    }
    offered: list[str] = []
    if succeeded:
        for item in batch.items:
            if len(offered) >= max_items:
                break
            if item.id in seen_ids or not eligible_for_query(item, query):
                continue
            item_key = source_item_key(item.id)
            if item_key not in offered:
                offered.append(item_key)
    if phase == "challenge":
        if not isinstance(source_operations, CheckpointedChallengeItems) or freeze is None:
            raise ValueError("Challenge settlement requires atomic frozen evidence")
        eligible = ResearchBatch(
            items=tuple(item for item in batch.items if source_item_key(item.id) in offered)
            if succeeded
            else (),
            attempts=batch.attempts,
        )
        selected = await freeze(eligible)
        if {item.event_id for item in selected} - {item.id for item in eligible.items}:
            raise ValueError("Frozen challenge evidence must come from this source result")
        status = (
            batch.attempts[0].status
            if not succeeded and batch.attempts
            else CollectionStatus.COMPLETED
            if selected
            else CollectionStatus.EMPTY
        )
        settlement = await source_operations.settle_challenge_operation(
            mode=query.mode,
            request_key=key,
            elapsed_ms=elapsed_ms,
            evidence=selected,
            attempt=CollectionAttempt(
                provider.id,
                provider.name,
                status,
                len(selected),
                "A fresh source request was completed."
                if succeeded
                else "The fresh source request did not complete.",
                task_id=task.task_id,
            ),
        )
    else:
        settlement = await source_operations.settle_source_operation(
            mode=query.mode,
            phase=phase,
            request_key=key,
            elapsed_ms=elapsed_ms,
            retained_item_keys=tuple(offered),
        )
    return ReservedFetch(batch, frozenset(settlement.retained_keys), CollectionStatus.EMPTY, "")

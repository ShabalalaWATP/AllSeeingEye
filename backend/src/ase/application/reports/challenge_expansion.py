"""One checkpointed post-draft source pass, with conservative interrupted receipts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research import (
    CheckpointedChallengeCollection,
    CheckpointedChallengeItems,
)
from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    PacketStatus,
    Status,
    parent_digest,
    query_digest,
    validate_lineage,
)
from ase.application.reports.challenge_expansion_selection import append_challenge_evidence
from ase.application.reports.challenge_models import challenge_call
from ase.application.reports.drafting import Draft
from ase.application.reports.frozen_challenge import review_frozen
from ase.application.reports.production_checkpoint import ExpansionCheckpoints, ProductionSnapshot
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.reports.progress import Progress, reached
from ase.application.reports.selection import Selection
from ase.domain.challenge import ChallengeSearch, ReportChallenge
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.evidence import EvidenceItem
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmRole
from ase.domain.project_lookup import preserve_project_lookup
from ase.domain.reports import Gap, ReportBody
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Finding, Severity

_DISPATCHED = {
    CollectionStatus.COMPLETED,
    CollectionStatus.EMPTY,
    CollectionStatus.FAILED,
    CollectionStatus.TIMED_OUT,
}


@dataclass(frozen=True, slots=True)
class ExpansionOutcome:
    draft: Draft
    selection: Selection
    body: ReportBody
    challenge: ReportChallenge


def _revised_query(query: ResearchQuery, terms: tuple[str, ...]) -> ResearchQuery:
    """Only terms change; area, time, languages, permission and source policy stay fixed."""
    return replace(
        query,
        terms=terms,
        query_variants=(),
        planned_tasks=(),
        candidate_hypotheses=(),
    )


async def _plan(
    job: Job,
    body: ReportBody,
    query: ResearchQuery,
    snapshot: ProductionSnapshot,
    collection: CheckpointedChallengeCollection | None,
    checkpoints: ExpansionCheckpoints,
    gateway: LlmGateway,
    cipher: SecretCipher,
    profile_for: ProfileLookup,
    totals: Totals,
) -> ExpansionPlan:
    parent, original = parent_digest(snapshot), query_digest(query)
    saved = await checkpoints.load_expansion_plan()
    if saved is not None:
        if (
            saved.parent != parent
            or saved.query != original
            or (
                saved.target_id is not None
                and saved.target_id not in {row.id for row in body.key_judgements}
            )
        ):
            raise ValueError("Challenge plan does not match its frozen first packet")
        return saved
    target: str | None = None
    terms: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    status: Status = "unavailable"
    if not body.key_judgements:
        status = "not_applicable"
    elif query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA} or query.area is not None:
        status = "unavailable"
    elif collection is not None:
        profile = await profile_for(LlmRole.DEVIL) or await profile_for(LlmRole.DIRECTION)
        if profile is not None:
            result = await challenge_call(
                gateway,
                profile,
                cipher.decrypt(profile.api_key_encrypted),
                body,
                languages=query.languages,
            )
            totals.usage.append(
                usage_entry(
                    job,
                    profile,
                    f"report:{job.template.id}:challenge:plan",
                    result.succeeded,
                    result,
                )
            )
            totals.add(
                result.prompt_tokens, result.completion_tokens, result.latency_ms, result.findings
            )
            target = next((row.id for row in body.key_judgements if row.id in result.plans), None)
            if target is not None:
                try:
                    terms = preserve_project_lookup(query.terms, result.plans[target])
                    sources = collection.plan_challenge(_revised_query(query, terms))
                except (ValueError, InvalidRequest):
                    sources = ()
                status = "ready" if sources else "unavailable"
    plan = ExpansionPlan(parent, original, target, terms, sources, status)
    await checkpoints.save_expansion_plan(plan)
    return plan


async def _packet(
    job: Job,
    query: ResearchQuery,
    snapshot: ProductionSnapshot,
    plan: ExpansionPlan,
    collection: CheckpointedChallengeCollection | None,
    source_operations: CheckpointedChallengeItems,
    checkpoints: ExpansionCheckpoints,
    profiles: Mapping[str, SourceProfile],
    progress: Progress | None,
) -> ExpansionPacket:
    saved = await checkpoints.load_expansion_packet()
    if saved is not None:
        validate_lineage(saved, plan, snapshot)
        return saved
    status: PacketStatus = "unavailable" if plan.status != "not_applicable" else "not_applicable"
    reason = "No permitted fresh challenge source was available."
    receipt = None
    added: tuple[EvidenceItem, ...] = ()
    if plan.status == "ready" and collection is not None:
        revised = _revised_query(query, plan.terms)
        interrupted = False

        async def freeze(batch: ResearchBatch) -> tuple[EvidenceItem, ...]:
            prior, _ = await source_operations.load_challenge_partial()
            selected = Selection(
                (*snapshot.selection.items, *prior),
                snapshot.selection.flagged,
                snapshot.selection.considered,
            )
            _, fresh = append_challenge_evidence(
                selected, batch, profiles, terms=plan.terms, mode=query.mode, now=job.now
            )
            return fresh

        try:
            await reached(progress, ResearchStage.COLLECTING)
            batch = await collection.collect_challenge_checkpointed(
                revised, plan.source_ids, source_operations, freeze
            )
        except (ValueError, InvalidRequest, RateLimited):
            batch = ResearchBatch()
            interrupted = True
        added, completed = await source_operations.load_challenge_partial()
        completed_keys = {(row.task_id, row.source_id) for row in completed}
        attempts = (
            *completed,
            *(row for row in batch.attempts if (row.task_id, row.source_id) not in completed_keys),
        )
        if attempts:
            receipt = ResearchReceipt.build(revised, attempts, len(added))
            status = (
                "attempted" if any(row.status in _DISPATCHED for row in attempts) else "interrupted"
            )
            reason = (
                "Fresh source requests were attempted; selected records are candidates, "
                "not verification."
                if status == "attempted"
                else "Earlier source operations could not safely be replayed after interruption."
            )
        elif interrupted:
            status = "interrupted"
            reason = "Challenge collection stopped before a complete source receipt was available."
    packet = ExpansionPacket(plan.parent, plan.fingerprint, added, receipt, status, reason)
    validate_lineage(packet, plan, snapshot)
    await checkpoints.save_expansion_packet(packet)
    return packet


def _searches(
    body: ReportBody, plan: ExpansionPlan, packet: ExpansionPacket, selected: Selection
) -> tuple[ChallengeSearch, ...]:
    retained = {row.event_id for row in selected.items}
    attempts = packet.receipt.attempts if packet.receipt else ()
    return tuple(
        ChallengeSearch(
            row.id,
            row.statement,
            plan.terms if row.id == plan.target_id else (),
            "attempted"
            if row.id == plan.target_id and packet.status == "attempted"
            else "budget_exhausted"
            if row.id == plan.target_id
            and any(attempt.status is CollectionStatus.BUDGET_EXHAUSTED for attempt in attempts)
            else "unavailable",
            attempts if row.id == plan.target_id else (),
            packet.receipt.collected_items if row.id == plan.target_id and packet.receipt else 0,
            tuple(item.event_id for item in packet.added if item.event_id in retained)
            if row.id == plan.target_id
            else (),
            packet.reason
            if row.id == plan.target_id
            else "This judgement was reviewed against existing evidence; "
            "no targeted fresh search was run.",
        )
        for row in body.key_judgements
    )


async def expand_and_review(
    job: Job,
    initial: Draft,
    snapshot: ProductionSnapshot,
    *,
    collection: CheckpointedChallengeCollection | None,
    source_operations: CheckpointedChallengeItems,
    checkpoints: ExpansionCheckpoints,
    profiles: Mapping[str, SourceProfile],
    gateway: LlmGateway,
    cipher: SecretCipher,
    profile_for: ProfileLookup,
    totals: Totals,
    redraft: Callable[[Selection], Awaitable[Draft]],
    progress: Progress | None,
) -> ExpansionOutcome:
    query = snapshot.query
    if query is None or not query.mode.requires_challenge:
        raise ValueError("A Deep or Advanced frozen research query is required")
    body = initial.body or ReportBody()
    plan = await _plan(
        job, body, query, snapshot, collection, checkpoints, gateway, cipher, profile_for, totals
    )
    packet = await _packet(
        job, query, snapshot, plan, collection, source_operations, checkpoints, profiles, progress
    )
    selection = snapshot.selection
    if packet.added:
        candidate = Selection(
            (*selection.items, *packet.added),
            selection.flagged,
            selection.considered + (packet.receipt.collected_items if packet.receipt else 0),
        )
        revised = await redraft(candidate)
        if revised.body is not None:
            for finding in initial.findings:
                if finding in totals.findings:
                    totals.findings.remove(finding)
            initial, selection, body = revised, candidate, revised.body
        else:
            body = replace(
                body,
                gaps=(*body.gaps, Gap("Fresh candidate evidence could not be safely redrafted.")),
            )
            totals.findings.append(
                Finding(
                    "challenge", Severity.WARNING, "challenge", "Fresh candidate redrafting failed."
                )
            )
    searches = _searches(body, plan, packet, selection)
    body, challenge = await review_frozen(
        job,
        body,
        selection,
        gateway=gateway,
        cipher=cipher,
        profile_for=profile_for,
        totals=totals,
        progress=progress,
        searches=searches,
        redrafted=selection is not snapshot.selection,
    )
    return ExpansionOutcome(initial, selection, body, challenge)

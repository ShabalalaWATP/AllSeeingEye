"""Restore or collect and freeze the inputs before any resumable report drafting."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research import ResearchCollection, SourceOperationCheckpoints
from ase.application.reports.area_context import AreaContextService, attach_area_context
from ase.application.reports.evidence_rerank import EvidenceReranker
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.original_followthrough import OriginalFollowThrough
from ase.application.reports.production_checkpoint import ProductionCheckpoints, ProductionSnapshot
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_model_roles import direct_for_job
from ase.application.reports.production_rerank import rerank_for_job
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Job, ProfileLookup, Totals
from ase.application.reports.progress import Progress, reached
from ase.application.reports.selection import Selection
from ase.domain.direction import Direction
from ase.domain.grading import SourceProfile
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_runs import ResearchStage


@dataclass(frozen=True, slots=True)
class PreparedProduction:
    snapshot: ProductionSnapshot | None
    source_operations: SourceOperationCheckpoints | None
    totals: Totals
    direction: Direction | None
    store: EventStore
    receipt: ResearchReceipt | None
    query: ResearchQuery | None
    selection: Selection
    select: Callable[[tuple[str, ...]], Selection]
    original_context: str


async def prepare_production(
    job: Job,
    profile_for: ProfileLookup,
    *,
    checkpoints: ProductionCheckpoints | None,
    gateway: LlmGateway,
    cipher: SecretCipher,
    research: ResearchCollection | None,
    private_store_factory: Callable[[], EventStore] | None,
    shared_store: EventStore,
    web_research: FreshWebResearch | None,
    reranker: EvidenceReranker | None,
    source_profiles: Mapping[str, SourceProfile],
    original_followthrough: OriginalFollowThrough | None,
    area_context: AreaContextService | None,
    progress: Progress | None,
) -> PreparedProduction:
    snapshot = await checkpoints.load_collection() if checkpoints is not None else None
    source_operations = (
        checkpoints
        if isinstance(checkpoints, SourceOperationCheckpoints) and checkpoints.source_phase_enabled
        else None
    )
    totals = (
        replace(
            snapshot.totals,
            findings=list(snapshot.totals.findings),
            usage=list(snapshot.totals.usage),
        )
        if snapshot is not None
        else Totals()
    )
    await reached(progress, ResearchStage.PLANNING)
    if snapshot is None:
        direction = await direct_for_job(job, profile_for, totals, gateway, cipher)
        store, receipt, query = await prepare_collection(
            job,
            direction,
            totals,
            research,
            private_store_factory,
            shared_store,
            progress,
            gateway=gateway,
            cipher=cipher,
            profile_for=profile_for,
            web_research=web_research,
            source_operations=source_operations,
        )
    else:
        direction, receipt, query = snapshot.direction, snapshot.receipt, snapshot.query
        store = shared_store

    # A resumed job keeps its frozen selection, so no second embedding call is made.
    # Only the unresumed path hands `select` to the challenge, so the challenge's
    # re-selection sees the same similarity map that produced the first selection.
    rerank = await rerank_for_job(
        reranker,
        job,
        store,
        direction,
        query,
        receipt,
        totals,
        profile_for,
        resumed=snapshot is not None,
    )

    def select(extra_terms: tuple[str, ...] = ()) -> Selection:
        return select_for_job(
            store,
            source_profiles,
            job,
            direction,
            extra_terms,
            runtime_query=query,
            receipt=receipt,
            reserve_challenge_slots=source_operations is not None,
            similarity=rerank.similarity,
            rerank_reason=rerank.reason,
        )

    selection = snapshot.selection if snapshot is not None else select()
    original_context = ""
    if receipt is not None and original_followthrough is not None:
        if snapshot is None:
            originals = await original_followthrough.collect(job, store, selection, receipt)
            receipt = replace(receipt, original_followup=originals)
        original_context = await original_followthrough.context(receipt.original_followup)
    receipt = await attach_area_context(area_context, job, query, selection, receipt, shared_store)
    if checkpoints is not None and snapshot is None:
        snapshot = ProductionSnapshot(
            selection,
            direction,
            receipt,
            query,
            replace(totals, findings=list(totals.findings), usage=list(totals.usage)),
        )
        await checkpoints.save_collection(snapshot)
    return PreparedProduction(
        snapshot,
        source_operations,
        totals,
        direction,
        store,
        receipt,
        query,
        selection,
        select,
        original_context,
    )

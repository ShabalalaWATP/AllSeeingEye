"""An on-demand provider performs a single bounded public collection request."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ase.application.research.phase_ledger import Phase, ReservationDecision, SettlementReceipt
from ase.domain.evidence import EvidenceItem
from ase.domain.research import CollectionAttempt, ResearchBatch, ResearchMode, ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_continuation import ContinuationTrace
from ase.domain.research_plan import ResearchPlan


@dataclass(frozen=True, slots=True)
class ContinuationProposal:
    query: ResearchQuery | None
    trace: ContinuationTrace
    # A pre-dispatch policy decision is distinct from an attempted, failed model call.
    model_called: bool = True


ReplanCallback = Callable[
    [ResearchQuery, ResearchBatch, float], Awaitable[ResearchQuery | ContinuationProposal | None]
]


class ResearchProvider(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    def supports(self, query: ResearchQuery) -> bool: ...

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        """Make at most one HTTP request, returning bounded items and safe receipts.

        Provider errors must not include query text, credentials or response bodies.
        Requests use the public-host guard. Pagination is a separate admitted call.
        """
        ...


class ResearchCollection(Protocol):
    def plan(self, query: ResearchQuery) -> ResearchPlan:
        """Preview concrete tasks without collection or model calls."""
        ...

    async def collect(
        self, query: ResearchQuery, *, replan: ReplanCallback | None = None
    ) -> ResearchBatch: ...

    async def challenge_many(self, queries: tuple[ResearchQuery, ...]) -> tuple[ResearchBatch, ...]:
        """One shared six-request/45-second/200-item budget, results in input order."""
        ...


@runtime_checkable
class RankedResearchCollection(Protocol):
    """Optional canonical-requirement collection supported by production services."""

    async def collect_with_requirements(
        self,
        query: ResearchQuery,
        requirements: tuple[IntelligenceRequirement, ...],
        *,
        replan: ReplanCallback | None = None,
    ) -> ResearchBatch: ...


@runtime_checkable
class SourceOperationCheckpoints(Protocol):
    """Lease-fenced durable source reservations for one report job."""

    @property
    def source_phase_enabled(self) -> bool: ...

    async def reserve_source_operation(
        self, *, mode: ResearchMode, phase: Phase, request_key: str
    ) -> ReservationDecision: ...

    async def settle_source_operation(
        self,
        *,
        mode: ResearchMode,
        phase: Phase,
        request_key: str,
        elapsed_ms: int,
        retained_item_keys: tuple[str, ...],
    ) -> SettlementReceipt: ...


@runtime_checkable
class CheckpointedChallengeItems(SourceOperationCheckpoints, Protocol):
    """Settle a challenge request with its frozen selected records in one write."""

    async def load_challenge_partial(
        self,
    ) -> tuple[tuple[EvidenceItem, ...], tuple[CollectionAttempt, ...]]: ...

    async def settle_challenge_operation(
        self,
        *,
        mode: ResearchMode,
        request_key: str,
        elapsed_ms: int,
        evidence: tuple[EvidenceItem, ...],
        attempt: CollectionAttempt,
    ) -> SettlementReceipt: ...


@runtime_checkable
class CheckpointedResearchCollection(Protocol):
    """Optional report-job collection that refuses unreserved source dispatch."""

    async def collect_checkpointed(
        self,
        query: ResearchQuery,
        requirements: tuple[IntelligenceRequirement, ...],
        source_operations: SourceOperationCheckpoints,
        *,
        replan: ReplanCallback | None = None,
    ) -> ResearchBatch: ...


@runtime_checkable
class CheckpointedChallengeCollection(Protocol):
    """A fresh post-draft pass against a saved, exact provider inventory."""

    def plan_challenge(self, query: ResearchQuery) -> tuple[str, ...]: ...

    async def collect_challenge_checkpointed(
        self,
        query: ResearchQuery,
        source_ids: tuple[str, ...],
        source_operations: CheckpointedChallengeItems,
        freeze: Callable[[ResearchBatch], Awaitable[tuple[EvidenceItem, ...]]],
    ) -> ResearchBatch: ...

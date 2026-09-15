"""Shared research admission with provider selection supplied by composition."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from ase.application.ports.research import (
    CheckpointedChallengeItems,
    ReplanCallback,
    ResearchProvider,
    SourceOperationCheckpoints,
)
from ase.application.research.allocated_plan import (
    AllocatedPlan,
    AllocationContext,
    allocate_plan_tasks,
)
from ase.application.research.challenge_collection import collect_challenges
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.application.research.planning import build_plan
from ase.application.research.replanning import collect_with_replan
from ase.application.research.reserved_collection import Freeze
from ase.domain.errors import RateLimited
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchBatch, ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_plan import ResearchPlan
from ase.domain.source_capabilities import DateSupport

AllocationLoader = Callable[[tuple[str, ...]], Awaitable[AllocationContext]]


def _accepted_dates(query: ResearchQuery) -> tuple[DateSupport, ...]:
    """Permit only date meanings the request can actually use."""
    if query.effective_time_basis is EvidenceTimeBasis.RECORDED:
        return (DateSupport.RECORDED_INTERVAL, DateSupport.ANNUAL_PERIODS)
    if query.effective_time_basis is EvidenceTimeBasis.RESEARCH:
        return (DateSupport.RESEARCH_INTERVAL, DateSupport.PUBLICATION_INTERVAL)
    return (DateSupport.PUBLICATION_INTERVAL, DateSupport.CURRENT_SNAPSHOT)


class ResearchCollectionService:
    def __init__(
        self,
        providers: Callable[[ResearchQuery], Sequence[ResearchProvider]],
        *,
        challenge_providers: Callable[[ResearchQuery], Sequence[ResearchProvider]] | None = None,
        allocation_loader: AllocationLoader | None = None,
    ) -> None:
        self._providers = providers
        self._challenge_providers = challenge_providers or providers
        self._allocation_loader = allocation_loader
        self._admission = asyncio.Semaphore(2)
        self._pacer = RequestPacer()

    def _paced(
        self, query: ResearchQuery, *, challenge: bool = False
    ) -> tuple[ResearchProvider, ...]:
        factory = self._challenge_providers if challenge else self._providers
        return tuple(
            PacedProvider(provider, self._pacer)
            for provider in factory(query)
            if not challenge or query.source_ids is None or provider.id in query.source_ids
        )

    def plan(self, query: ResearchQuery) -> ResearchPlan:
        providers = tuple(self._providers(query))
        ResearchCollector(providers)
        limits = (
            CollectionBudget.for_initial_mode(query.mode)
            if self._allocation_loader is not None
            else CollectionBudget.for_mode(query.mode)
        )
        return build_plan(
            query, providers, requests=limits.requests, seconds=limits.seconds, items=limits.items
        )

    async def collect(
        self, query: ResearchQuery, *, replan: ReplanCallback | None = None
    ) -> ResearchBatch:
        return await self.collect_with_requirements(query, (), replan=replan)

    async def collect_with_requirements(
        self,
        query: ResearchQuery,
        requirements: tuple[IntelligenceRequirement, ...],
        *,
        replan: ReplanCallback | None = None,
    ) -> ResearchBatch:
        return await self._collect(query, requirements, replan=replan)

    async def collect_checkpointed(
        self,
        query: ResearchQuery,
        requirements: tuple[IntelligenceRequirement, ...],
        source_operations: SourceOperationCheckpoints,
        *,
        replan: ReplanCallback | None = None,
    ) -> ResearchBatch:
        return await self._collect(
            query, requirements, replan=replan, source_operations=source_operations
        )

    async def _collect(
        self,
        query: ResearchQuery,
        requirements: tuple[IntelligenceRequirement, ...],
        *,
        replan: ReplanCallback | None,
        source_operations: SourceOperationCheckpoints | None = None,
    ) -> ResearchBatch:
        """Collect the frozen plan after current source allocation, when configured."""
        if self._admission.locked():
            raise RateLimited(5)
        async with self._admission:
            providers = self._paced(query)
            loader = self._allocation_loader
            if loader is not None:
                limits = CollectionBudget.for_initial_mode(query.mode)

                async def allocate(candidate: ResearchQuery) -> AllocatedPlan:
                    frozen = build_plan(
                        candidate,
                        providers,
                        requests=limits.requests,
                        seconds=limits.seconds,
                        items=limits.items,
                    )
                    context = await loader(tuple(row.id for row in providers))
                    return allocate_plan_tasks(
                        candidate,
                        frozen,
                        requirements,
                        context,
                        accepted_dates=_accepted_dates(candidate),
                    )

                first = await allocate(query)
                if replan is not None:
                    return await collect_with_replan(
                        providers,
                        query,
                        replan,
                        initial_budget=limits,
                        first_allocation=first,
                        allocate=allocate,
                        source_operations=source_operations,
                    )
                return await ResearchCollector(providers).collect(
                    query,
                    budget=limits,
                    allocated_plan=first,
                    source_operations=source_operations,
                )
            if replan is not None:
                return await collect_with_replan(
                    providers, query, replan, source_operations=source_operations
                )
            return await ResearchCollector(providers).collect(
                query, source_operations=source_operations
            )

    async def challenge_many(self, queries: tuple[ResearchQuery, ...]) -> tuple[ResearchBatch, ...]:
        if self._admission.locked():
            raise RateLimited(5)
        async with self._admission:
            return await collect_challenges(
                tuple(
                    replace(query, query_variants=(), planned_tasks=(), candidate_hypotheses=())
                    for query in queries
                ),
                lambda query: self._paced(query, challenge=True),
            )

    def plan_challenge(self, query: ResearchQuery) -> tuple[str, ...]:
        """Freeze only supported, permitted providers before a durable challenge."""
        budget = CollectionBudget.for_challenge_mode(query.mode)
        if budget is None:
            return ()
        clean = replace(query, query_variants=(), planned_tasks=(), candidate_hypotheses=())
        providers = self._paced(clean, challenge=True)
        ResearchCollector(providers)
        return tuple(provider.id for provider in providers if provider.supports(clean))[
            : budget.requests
        ]

    async def collect_challenge_checkpointed(
        self,
        query: ResearchQuery,
        source_ids: tuple[str, ...],
        source_operations: CheckpointedChallengeItems,
        freeze: Freeze,
    ) -> ResearchBatch:
        """One extra acquisition pass; every request reserves the challenge phase."""
        budget = CollectionBudget.for_challenge_mode(query.mode)
        if budget is None or not source_ids:
            return ResearchBatch()
        if source_ids != self.plan_challenge(query):
            raise ValueError("The frozen challenge source inventory is no longer available")
        if self._admission.locked():
            raise RateLimited(5)
        clean = replace(
            query,
            source_ids=source_ids,
            query_variants=(),
            planned_tasks=(),
            candidate_hypotheses=(),
        )
        async with self._admission:
            return await ResearchCollector(self._paced(clean, challenge=True)).collect(
                clean,
                budget=budget,
                source_operations=source_operations,
                phase="challenge",
                freeze=freeze,
            )

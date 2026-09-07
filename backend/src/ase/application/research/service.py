"""Shared research admission with provider selection supplied by composition."""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import replace

from ase.application.ports.research import ReplanCallback, ResearchProvider
from ase.application.research.challenge_collection import collect_challenges
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.application.research.planning import build_plan
from ase.application.research.replanning import collect_with_replan
from ase.domain.errors import RateLimited
from ase.domain.research import ResearchBatch, ResearchQuery
from ase.domain.research_plan import ResearchPlan


class ResearchCollectionService:
    def __init__(
        self,
        providers: Callable[[ResearchQuery], Sequence[ResearchProvider]],
        *,
        challenge_providers: Callable[[ResearchQuery], Sequence[ResearchProvider]] | None = None,
    ) -> None:
        self._providers = providers
        self._challenge_providers = challenge_providers or providers
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
        limits = CollectionBudget.for_mode(query.mode)
        return build_plan(
            query, providers, requests=limits.requests, seconds=limits.seconds, items=limits.items
        )

    async def collect(
        self, query: ResearchQuery, *, replan: ReplanCallback | None = None
    ) -> ResearchBatch:
        if self._admission.locked():
            raise RateLimited(5)
        async with self._admission:
            providers = self._paced(query)
            if replan is not None:
                return await collect_with_replan(providers, query, replan)
            return await ResearchCollector(providers).collect(query)

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

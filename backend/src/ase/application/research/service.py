"""Shared research admission with provider selection supplied by composition."""

import asyncio
from collections.abc import Callable, Sequence

from ase.application.ports.research import ResearchProvider
from ase.application.research.challenge_collection import collect_challenges
from ase.application.research.collection import ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.domain.errors import RateLimited
from ase.domain.research import ResearchBatch, ResearchQuery


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
        return tuple(PacedProvider(provider, self._pacer) for provider in factory(query))

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if self._admission.locked():
            raise RateLimited(5)
        async with self._admission:
            return await ResearchCollector(self._paced(query)).collect(query)

    async def challenge_many(self, queries: tuple[ResearchQuery, ...]) -> tuple[ResearchBatch, ...]:
        if self._admission.locked():
            raise RateLimited(5)
        async with self._admission:
            return await collect_challenges(
                queries, lambda query: self._paced(query, challenge=True)
            )

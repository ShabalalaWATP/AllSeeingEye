"""Shared pacing across research sources, including SEC fair-access requests."""

import asyncio

from ase.application.ports.research import ResearchProvider
from ase.application.research.provider_capabilities import ProviderDecorator
from ase.domain.research import ResearchBatch, ResearchQuery


class RequestPacer:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_start = float("-inf")

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            delay = self._last_start + 0.125 - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_start = loop.time()


class PacedProvider(ProviderDecorator):
    def __init__(self, provider: ResearchProvider, pacer: RequestPacer) -> None:
        super().__init__(provider)
        self._pacer = pacer

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        await self._pacer.wait()
        return await self._provider.collect(query)

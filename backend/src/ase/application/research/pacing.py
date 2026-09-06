"""Shared pacing across research sources, including SEC fair-access requests."""

import asyncio

from ase.application.ports.research import ResearchProvider
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


class PacedProvider:
    def __init__(self, provider: ResearchProvider, pacer: RequestPacer) -> None:
        self._provider, self._pacer = provider, pacer

    @property
    def id(self) -> str:
        return self._provider.id

    @property
    def name(self) -> str:
        return self._provider.name

    def supports(self, query: ResearchQuery) -> bool:
        return self._provider.supports(query)

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        await self._pacer.wait()
        return await self._provider.collect(query)

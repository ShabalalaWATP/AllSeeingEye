"""Shared pacing across research sources, including SEC fair-access requests."""

import asyncio

from ase.application.ports.research import ResearchProvider
from ase.domain.research import ResearchBatch, ResearchQuery
from ase.domain.research_plan import UNKNOWN_SPATIAL_SCOPE, UNKNOWN_TEMPORAL_SCOPE


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

    @property
    def language(self) -> str | None:
        value = getattr(self._provider, "language", None)
        return value if isinstance(value, str) else None

    @property
    def temporal_scope(self) -> str:
        value = getattr(self._provider, "temporal_scope", UNKNOWN_TEMPORAL_SCOPE)
        return value if isinstance(value, str) else UNKNOWN_TEMPORAL_SCOPE

    @property
    def query_language_aliases(self) -> tuple[str, ...]:
        values = getattr(self._provider, "query_language_aliases", ())
        return tuple(value for value in values if isinstance(value, str))

    def supports(self, query: ResearchQuery) -> bool:
        return self._provider.supports(query)

    def supports_area(self, query: ResearchQuery) -> bool:
        hook = getattr(self._provider, "supports_area", None)
        return callable(hook) and hook(query) is True

    @property
    def spatial_scope(self) -> str:
        value = getattr(self._provider, "spatial_scope", UNKNOWN_SPATIAL_SCOPE)
        return value if isinstance(value, str) else UNKNOWN_SPATIAL_SCOPE

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        await self._pacer.wait()
        return await self._provider.collect(query)

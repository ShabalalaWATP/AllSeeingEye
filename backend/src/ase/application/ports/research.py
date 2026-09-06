"""An on-demand provider performs a single bounded public collection request."""

from typing import Protocol

from ase.domain.research import ResearchBatch, ResearchQuery


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
    async def collect(self, query: ResearchQuery) -> ResearchBatch: ...

    async def challenge_many(self, queries: tuple[ResearchQuery, ...]) -> tuple[ResearchBatch, ...]:
        """One shared six-request/45-second/200-item budget, results in input order."""
        ...

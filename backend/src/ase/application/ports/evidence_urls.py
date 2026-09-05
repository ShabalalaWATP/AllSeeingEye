"""Resolve a cited evidence link without collecting an article's body."""

from typing import Protocol


class EvidenceUrlResolver(Protocol):
    async def resolve(self, url: str) -> str | None:
        """A verified publisher URL, or None when compliant resolution is unavailable."""
        ...

"""Metadata-only footprint search boundary."""

from typing import Protocol

from ase.domain.footprints import FootprintCollection, FootprintQuery


class FootprintProvider(Protocol):
    async def search(self, query: FootprintQuery) -> FootprintCollection: ...

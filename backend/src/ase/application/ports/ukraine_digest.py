"""Storage for the small bounded history of Ukraine digests."""

from __future__ import annotations

from typing import Protocol

from ase.domain.ukraine.digest import StoredDigest


class UkraineDigestStore(Protocol):
    async def recent(self, limit: int) -> list[StoredDigest]:
        """The newest digests first, at most ``limit`` of them."""
        ...

    async def save(self, digest: StoredDigest, keep: int) -> None:
        """Store one digest and drop everything beyond the newest ``keep``."""
        ...

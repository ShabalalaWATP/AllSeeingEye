"""Embeddings have their own provider boundary and bounded report-only storage."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from ase.domain.report_search import EmbeddingResult, IndexedReport


class EmbeddingGatewayError(Exception):
    """An endpoint failed; no remote body, credential or user text belongs in the error."""


class EmbeddingGateway(Protocol):
    async def embed(
        self, base_url: str, api_key: str, model: str, texts: Sequence[str]
    ) -> EmbeddingResult: ...


class ReportEmbeddingRepository(Protocol):
    async def current(
        self, report_ids: Sequence[UUID], fingerprint: str
    ) -> list[IndexedReport]: ...

    async def save(self, entry: IndexedReport) -> bool:
        """Save only if this version is still current and its report still exists."""
        ...

    async def prune_obsolete(self) -> None:
        """Remove deleted or superseded versions without evicting another scope."""
        ...

    async def capacity_for(self, report_ids: Sequence[UUID], limit: int) -> frozenset[UUID]:
        """Existing slots plus requested new slots fitting the shared storage limit."""
        ...

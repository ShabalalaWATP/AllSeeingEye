"""Persistence boundary for append-only human citation verdicts on exact report versions."""

from typing import Protocol
from uuid import UUID

from ase.domain.citation_verdicts import CitationAnchor, CitationVerdict


class CitationVerdictRepository(Protocol):
    async def for_version(self, report_version_id: UUID, limit: int) -> tuple[CitationVerdict, ...]:
        """Oldest first, at most `limit` verdicts recorded on the exact version."""
        ...

    async def count_for_version(self, report_version_id: UUID) -> int: ...

    async def count_for_anchor(self, report_version_id: UUID, anchor: CitationAnchor) -> int: ...

    async def add(self, verdict: CitationVerdict) -> None: ...

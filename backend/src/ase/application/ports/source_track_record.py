"""Read-only boundary for one source's citations in the caller's visible saved reports."""

from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.citation_verdicts import CitationVerdict
from ase.domain.source_reviews import SourceReviewRevision
from ase.domain.source_track_record import TrackRecordPopulation


class SourceTrackRecordReader(Protocol):
    async def population(
        self, visibility: Visibility, source_id: str, limit: int
    ) -> TrackRecordPopulation:
        """Visibility first, then the latest `limit` reports, then their latest versions."""
        ...

    async def reviews(
        self, visibility: Visibility, source_id: str, report_ids: frozenset[UUID], limit: int
    ) -> tuple[SourceReviewRevision, ...]:
        """Current visible reviewer decisions about the source on the given reports."""
        ...

    async def verdicts(
        self, visibility: Visibility, versions: frozenset[tuple[UUID, int]], limit: int
    ) -> tuple[CitationVerdict, ...]:
        """Visible verdicts on the exact versions, recorded in each report's current scope."""
        ...

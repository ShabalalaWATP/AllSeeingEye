"""Read-only boundary for the administrator research-quality scorecard."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from ase.domain.access import Visibility
from ase.domain.citation_verdicts import CitationVerdict
from ase.domain.research_quality import JobOutcome, VersionOutcome


class ResearchQualityReader(Protocol):
    async def versions(
        self, visibility: Visibility, since: datetime, limit: int
    ) -> tuple[int, Sequence[VersionOutcome]]:
        """Visible saved versions since `since`: the full count, then the latest `limit`."""
        ...

    async def jobs(
        self, visibility: Visibility, since: datetime, limit: int
    ) -> tuple[int, Sequence[JobOutcome]]:
        """Visible report jobs created since `since`: the full count, then the latest `limit`."""
        ...

    async def citation_verdicts(
        self, visibility: Visibility, since: datetime, limit: int
    ) -> tuple[int, Sequence[CitationVerdict]]:
        """Visible verdicts recorded since `since`: the full count, then the latest `limit`."""
        ...

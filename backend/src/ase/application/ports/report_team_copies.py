"""Port for team copy provenance and the personal records a copy never carries."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.report_team_copy import LinkedArtefacts, ReportTeamCopy


class ReportTeamCopyRepository(Protocol):
    async def find(self, source_version_id: UUID, team_id: UUID) -> ReportTeamCopy | None: ...

    async def for_report(self, report_id: UUID) -> ReportTeamCopy | None: ...

    async def add(self, copy: ReportTeamCopy) -> None:
        """Raise Conflict when this source version already has a copy in the team."""
        ...

    async def linked_artefacts(self, version_id: UUID) -> LinkedArtefacts: ...

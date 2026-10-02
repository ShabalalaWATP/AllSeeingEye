"""Storage port for exact-version, append-only report ledgers."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.forecast_views import ForecastIndex
from ase.domain.report_ledgers import LedgerEntry, ReportLedger, ReportLedgerAnchor


class ReportLedgerRepository(Protocol):
    async def get(self, ledger_id: UUID) -> ReportLedger | None: ...
    async def list_ids(
        self, report_version_id: UUID, limit: int, offset: int
    ) -> tuple[tuple[UUID, ...], int]: ...
    async def create(self, anchor: ReportLedgerAnchor, first: LedgerEntry) -> bool: ...
    async def append(self, anchor: ReportLedgerAnchor, entry: LedgerEntry) -> bool: ...

    async def append_many(
        self, anchor: ReportLedgerAnchor, entries: tuple[LedgerEntry, ...]
    ) -> bool: ...

    async def forecast_index(
        self, visibility: Visibility, team_id: UUID | None, personal: bool, limit: int, offset: int
    ) -> tuple[tuple[ForecastIndex, ...], int]: ...
    async def remind(
        self, anchor: ReportLedgerAnchor, version_id: UUID, review_at: datetime, now: datetime
    ) -> datetime: ...

"""Storage port for exact-version, append-only report ledgers."""

from typing import Protocol
from uuid import UUID

from ase.domain.report_ledgers import LedgerEntry, ReportLedger, ReportLedgerAnchor


class ReportLedgerRepository(Protocol):
    async def get(self, ledger_id: UUID) -> ReportLedger | None: ...
    async def list_ids(
        self, report_version_id: UUID, limit: int, offset: int
    ) -> tuple[tuple[UUID, ...], int]: ...
    async def create(self, anchor: ReportLedgerAnchor, first: LedgerEntry) -> bool: ...
    async def append(self, anchor: ReportLedgerAnchor, entry: LedgerEntry) -> bool: ...

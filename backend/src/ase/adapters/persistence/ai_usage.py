"""SQL persistence for AI policies, counters, reservations and observed totals."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.ai_usage_ledger import SqlAiLedger
from ase.adapters.persistence.ai_usage_policies import SqlAiPolicyStore
from ase.adapters.persistence.ai_usage_totals import SqlAiTotalsReader


class SqlAiUsageRepository(SqlAiPolicyStore, SqlAiLedger, SqlAiTotalsReader):
    """Policy and ledger adapter. Callers own the transaction and commit boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

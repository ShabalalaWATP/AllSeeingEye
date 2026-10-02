"""Scoped watch and count projections with the same exact-version ledger checks."""

from datetime import datetime
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.reports.ledger_access import ReportLedgerAccess
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.forecast_decisions import ForecastLedger
from ase.domain.forecast_ledger import ForecastState
from ase.domain.forecast_views import ForecastCounts, ForecastWatch, count_versions, version_state
from ase.domain.report_ledgers import ReportLedger

MAX_COHORT_LEDGERS = 1000


class ForecastViews(ReportLedgerAccess):
    async def watches(
        self,
        claims: AccessClaims,
        team_id: UUID | None,
        personal: bool,
        limit: int,
        offset: int,
    ) -> tuple[tuple[ForecastWatch, ...], int]:
        access = await self._context(claims)
        if team_id is not None:
            access.require_read(None, team_id)
        rows, total = await self.ledgers.forecast_index(
            access.visibility, team_id, personal, limit, offset
        )
        watches = []
        now = self.clock.now()
        for row in rows:
            ledger, _ = await self._existing(
                access, row.report_id, row.report_version, row.ledger_id
            )
            if not isinstance(ledger.history, ForecastLedger):
                continue
            current = ledger.history.current_version
            state = version_state(ledger.history, current, now)
            due = now >= current.review_at and state in (ForecastState.OPEN, ForecastState.DUE)
            reminded_at = None
            team = access.teams.get(ledger.anchor.team_id) if ledger.anchor.team_id else None
            if due and (team is None or team.is_active):
                reminded_at = await self.ledgers.remind(
                    ledger.anchor, UUID(current.version_id), current.review_at, now
                )
            watches.append(
                ForecastWatch(
                    row.ledger_id,
                    row.report_id,
                    row.report_version,
                    row.title,
                    current.version_id,
                    current.review_at,
                    current.horizon_end,
                    state,
                    due,
                    reminded_at,
                    ledger.anchor.team_id,
                )
            )
        await self._commit(claims)
        return tuple(watches), total

    async def counts(
        self,
        claims: AccessClaims,
        team_id: UUID | None,
        personal: bool,
        since: datetime,
        until: datetime,
    ) -> ForecastCounts:
        if since.utcoffset() is None or until.utcoffset() is None or not since < until:
            raise InvalidRequest("Choose a valid aware issue-time cohort window.")
        access = await self._context(claims)
        if team_id is not None:
            access.require_read(None, team_id)
        rows, total = await self.ledgers.forecast_index(
            access.visibility,
            team_id,
            personal,
            MAX_COHORT_LEDGERS,
            0,
        )
        if total > MAX_COHORT_LEDGERS:
            raise InvalidRequest(
                "This scope exceeds 1,000 forecast ledgers. Select a narrower scope."
            )
        histories = []
        for row in rows:
            ledger, _ = await self._existing(
                access, row.report_id, row.report_version, row.ledger_id
            )
            if isinstance(ledger.history, ForecastLedger):
                histories.append(ledger.history)
        result = count_versions(tuple(histories), since, until, self.clock.now())
        await self._commit(claims)
        return result

    async def export_forecasts(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        ledger_ids: tuple[UUID, ...],
    ) -> tuple[ReportLedger, ...]:
        if not 1 <= len(ledger_ids) <= 20 or len(set(ledger_ids)) != len(ledger_ids):
            raise InvalidRequest("Select between one and 20 distinct forecast histories.")
        access = await self._context(claims)
        rows = []
        for ledger_id in ledger_ids:
            ledger, _ = await self._existing(access, report_id, number, ledger_id)
            if not isinstance(ledger.history, ForecastLedger):
                raise NotFound()
            rows.append(ledger)
        await self._commit(claims)
        return tuple(rows)

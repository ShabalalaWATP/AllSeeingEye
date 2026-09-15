"""Authorised forecast and indicator actions; numeric source attestations are unavailable."""

from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.dto import AccessClaims, RequestContext
from ase.application.reports.ledger_access import ReportLedgerAccess
from ase.application.reports.ledger_inputs import (
    ForecastCreate,
    ForecastReview,
    IndicatorCreate,
    MissingReading,
)
from ase.domain.audit import AuditAction
from ase.domain.claim_revisions import ClaimRelation
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.forecast_decisions import ForecastDecision, ForecastLedger
from ase.domain.forecast_ledger import DecisionMethod, ForecastState, ForecastVersion
from ase.domain.indicator_ledger import IndicatorLedger, IndicatorReading, IndicatorVersion
from ase.domain.report_ledgers import LedgerKind, ReportLedger


class ReportLedgers(ReportLedgerAccess):
    async def create_forecast(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        value: ForecastCreate,
        context: RequestContext,
    ) -> ReportLedger:
        access = await self._context(claims)
        report, version = await self._report(access, report_id, number, write=True)
        anchor, revision = await self._anchor(
            access, report, version, value.claim_id, value.claim_revision_id
        )
        try:
            first = ForecastVersion(
                str(anchor.id),
                str(uuid4()),
                1,
                str(anchor.claim_id),
                str(anchor.claim_revision_id),
                str(version.id),
                anchor.created_at,
                value.horizon_end,
                value.review_at,
                value.criterion,
                value.likelihood,
                value.confidence,
                self._references(version, revision, value.supporting, ClaimRelation.SUPPORTING),
                self._references(version, revision, value.contrary, ClaimRelation.OPPOSING),
            )
            history = ForecastLedger((first,))
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if not await self.ledgers.create(anchor, first):
            raise Conflict("A forecast ledger with this identity already exists.")
        await self._audit(AuditAction.FORECAST_LEDGER_UPDATED, access, anchor.id, context)
        await self._commit(claims)
        return ReportLedger(anchor, history)

    async def create_indicator(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        value: IndicatorCreate,
        context: RequestContext,
    ) -> ReportLedger:
        access = await self._context(claims)
        report, version = await self._report(access, report_id, number, write=True)
        anchor, revision = await self._anchor(
            access, report, version, value.claim_id, value.claim_revision_id
        )
        try:
            refs = self._references(version, revision, (value.source_citation,))
            source = next(item for item in version.evidence if item.label == refs[0].evidence_id)
            if source.source_id != value.source_id:
                raise ValueError("Indicator source must match the frozen cited source")
            anchor = replace(anchor, kind=LedgerKind.INDICATOR, source_reference=refs[0])
            first = IndicatorVersion(
                str(anchor.id),
                str(uuid4()),
                1,
                value.condition,
                value.metric_id,
                value.unit,
                value.source_id,
                value.source_capability,
                value.expected_update_hours,
                anchor.created_at,
                value.threshold,
                value.direction,
                None,
                source_reference=refs[0],
            )
            history = IndicatorLedger((first,))
        except (ValueError, StopIteration) as exc:
            raise InvalidRequest(
                "Indicator does not match its frozen source or threshold."
            ) from exc
        if not await self.ledgers.create(anchor, first):
            raise Conflict("An indicator ledger with this identity already exists.")
        await self._audit(AuditAction.INDICATOR_LEDGER_UPDATED, access, anchor.id, context)
        await self._commit(claims)
        return ReportLedger(anchor, history)

    async def get(
        self, claims: AccessClaims, report_id: UUID, number: int, ledger_id: UUID
    ) -> ReportLedger:
        access = await self._context(claims)
        ledger, _ = await self._existing(access, report_id, number, ledger_id)
        await self._commit(claims)
        return ledger

    async def list(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        limit: int,
        offset: int,
    ) -> tuple[tuple[ReportLedger, ...], int]:
        if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
            raise InvalidRequest("Invalid ledger page bounds.")
        access = await self._context(claims)
        _, version = await self._report(access, report_id, number)
        ids, total = await self.ledgers.list_ids(version.id, limit, offset)
        rows = []
        for ledger_id in ids:
            ledger, _ = await self._existing(access, report_id, number, ledger_id)
            rows.append(ledger)
        await self._commit(claims)
        return tuple(rows), total

    async def decide(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        ledger_id: UUID,
        value: ForecastReview,
        context: RequestContext,
    ) -> ReportLedger:
        access = await self._context(claims)
        ledger, revision = await self._existing(access, report_id, number, ledger_id, write=True)
        if ledger.anchor.kind is not LedgerKind.FORECAST or not isinstance(
            ledger.history, ForecastLedger
        ):
            raise NotFound()
        history = ledger.history
        previous = history.latest_decision(history.current_version.version_id)
        if (str(value.previous_decision_id) if value.previous_decision_id else None) != (
            previous.id if previous else None
        ):
            raise Conflict("This forecast has a newer decision. Reload it before review.")
        _, version = await self._report(access, report_id, number)
        try:
            if value.state is not ForecastState.UNRESOLVED:
                raise ValueError(
                    "Outcome resolution needs later, independently frozen observations"
                )
            decision = ForecastDecision(
                str(uuid4()),
                history.current_version.version_id,
                previous.id if previous else None,
                self.clock.now(),
                value.state,
                DecisionMethod.REVIEWER,
                str(access.actor.id),
                value.reason,
                self._references(version, revision, value.evidence),
                None,
                None,
                str(value.corrects_decision_id) if value.corrects_decision_id else None,
            )
            updated = history.append(decision)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if not await self.ledgers.append(ledger.anchor, decision):
            raise Conflict("This forecast changed during review. Reload it.")
        await self._audit(AuditAction.FORECAST_LEDGER_UPDATED, access, ledger_id, context)
        await self._commit(claims)
        return ReportLedger(
            replace(ledger.anchor, latest_ordinal=ledger.anchor.latest_ordinal + 1), updated
        )

    async def record_missing(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        ledger_id: UUID,
        value: MissingReading,
        context: RequestContext,
    ) -> ReportLedger:
        access = await self._context(claims)
        ledger, _ = await self._existing(access, report_id, number, ledger_id, write=True)
        if ledger.anchor.kind is not LedgerKind.INDICATOR or not isinstance(
            ledger.history, IndicatorLedger
        ):
            raise NotFound()
        now = self.clock.now()
        if value.observed_at.utcoffset() is None or value.observed_at > now:
            raise InvalidRequest("Missing observation time must be a past, aware date.")
        try:
            reading = IndicatorReading(
                str(uuid4()),
                ledger.history.versions[-1].version_id,
                value.observed_at,
                now,
                ledger.history.versions[-1].unit,
                None,
                None,
                None,
                value.missing_reason,
                str(value.corrects_reading_id) if value.corrects_reading_id else None,
            )
            updated = ledger.history.append(reading)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if not await self.ledgers.append(ledger.anchor, reading):
            raise Conflict("This indicator changed during review. Reload it.")
        await self._audit(AuditAction.INDICATOR_LEDGER_UPDATED, access, ledger_id, context)
        await self._commit(claims)
        return ReportLedger(
            replace(ledger.anchor, latest_ordinal=ledger.anchor.latest_ordinal + 1), updated
        )

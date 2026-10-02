"""Later frozen outcome evidence and atomic, append-only forecast supersession."""

from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.access import AccessContext
from ase.application.dto import AccessClaims, RequestContext
from ase.application.reports.ledger_access import ReportLedgerAccess
from ase.application.reports.ledger_inputs import ForecastSupersession, OutcomeEvidence
from ase.domain.audit import AuditAction
from ase.domain.claim_revisions import ClaimRelation, ClaimReviewState
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.forecast_decisions import ForecastDecision, ForecastLedger
from ase.domain.forecast_ledger import (
    DecisionMethod,
    ForecastState,
    ForecastVersion,
    PassageReference,
)
from ase.domain.report_ledgers import ReportLedger


class ForecastLifecycle(ReportLedgerAccess):
    async def _outcome_references(
        self,
        access: AccessContext,
        ledger: ReportLedger,
        rows: tuple[OutcomeEvidence, ...],
    ) -> tuple[PassageReference, ...]:
        if not isinstance(ledger.history, ForecastLedger) or not 1 <= len(rows) <= 20:
            raise InvalidRequest("Resolution requires later independently frozen outcome evidence.")
        forecast = ledger.history.current_version
        refs = []
        for row in rows:
            report, version = await self._report(access, row.report_id, row.version)
            access.require_same_scope(
                ledger.anchor.owner_id, ledger.anchor.team_id, report.created_by, report.team_id
            )
            if (
                version.id == ledger.anchor.report_version_id
                or version.created_at <= forecast.issued_at
            ):
                raise InvalidRequest(
                    "Outcome evidence must be frozen independently after forecast issue."
                )
            _, revision = await self._claim(
                access, report, version, row.claim_id, row.claim_revision_id
            )
            if revision.state is not ClaimReviewState.REVIEWED:
                raise InvalidRequest("Review the exact outcome claim revision first.")
            ref = self._references(version, revision, (row.citation,))[0]
            evidence = next(item for item in version.evidence if item.label == ref.evidence_id)
            observed = evidence.published_at or evidence.observed_at
            if observed is None or not forecast.issued_at < observed <= self.clock.now():
                raise InvalidRequest(
                    "Outcome evidence requires a known observation later than forecast issue."
                )
            refs.append(ref)
        if len(set(refs)) != len(refs):
            raise InvalidRequest("Choose distinct outcome references.")
        return tuple(refs)

    async def supersede(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        ledger_id: UUID,
        value: ForecastSupersession,
        context: RequestContext,
    ) -> ReportLedger:
        access = await self._context(claims)
        ledger, revision = await self._existing(access, report_id, number, ledger_id, write=True)
        if not isinstance(ledger.history, ForecastLedger):
            raise NotFound()
        history = ledger.history
        current = history.current_version
        previous = history.latest_decision(current.version_id)
        if str(value.expected_version_id) != current.version_id or (
            str(value.previous_decision_id) if value.previous_decision_id else None
        ) != (previous.id if previous else None):
            raise Conflict("This forecast changed. Reload before superseding it.")
        replacement = value.replacement
        if (replacement.claim_id, replacement.claim_revision_id) != (
            ledger.anchor.claim_id,
            ledger.anchor.claim_revision_id,
        ):
            raise InvalidRequest("A replacement retains this ledger's exact reviewed claim anchor.")
        _, edition = await self._report(access, report_id, number)
        now = self.clock.now()
        try:
            updated = ForecastVersion(
                str(ledger_id),
                str(uuid4()),
                current.version + 1,
                current.claim_id,
                current.claim_version_id,
                current.report_version_id,
                now,
                replacement.horizon_end,
                replacement.review_at,
                replacement.criterion,
                replacement.likelihood,
                replacement.confidence,
                self._references(
                    edition, revision, replacement.supporting, ClaimRelation.SUPPORTING
                ),
                self._references(edition, revision, replacement.contrary, ClaimRelation.OPPOSING),
                current.version_id,
            )
            decision = ForecastDecision(
                str(uuid4()),
                current.version_id,
                previous.id if previous else None,
                now,
                ForecastState.SUPERSEDED,
                DecisionMethod.REVIEWER,
                str(access.actor.id),
                value.reason,
                superseding_version_id=updated.version_id,
            )
            result = history.supersede(updated, decision)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if not await self.ledgers.append_many(ledger.anchor, (updated, decision)):
            raise Conflict("This forecast changed during supersession. Reload it.")
        await self._audit(AuditAction.FORECAST_LEDGER_UPDATED, access, ledger_id, context)
        await self._commit(claims)
        return ReportLedger(
            replace(ledger.anchor, latest_ordinal=ledger.anchor.latest_ordinal + 2), result
        )

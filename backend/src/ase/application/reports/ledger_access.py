"""Shared authorisation and exact-claim citation checks for report ledgers."""

from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.claims import ClaimRepository
from ase.application.ports.report_ledgers import ReportLedgerRepository
from ase.application.ports.reports import ReportRepository
from ase.application.reports.ledger_inputs import CitationKey
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.audit import AuditAction
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimRelation,
    ClaimReviewState,
    ClaimRevision,
    freeze_claim_citations,
)
from ase.domain.claim_roots import ClaimRoot
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.forecast_ledger import PassageReference
from ase.domain.report_ledgers import LedgerKind, ReportLedger, ReportLedgerAnchor
from ase.domain.report_records import ReportRecord, ReportVersion

MAX_LEDGERS_PER_VERSION = 64


class ReportLedgerAccess:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        reports: ReportRepository,
        claims: ClaimRepository,
        ledgers: ReportLedgerRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports = users, refresh, reports
        self.claims, self.ledgers, self.access = claims, ledgers, access
        self.clock, self.auditor, self.uow = clock, auditor, uow

    async def _context(self, claims: AccessClaims) -> AccessContext:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        return await self.access.context(actor)

    async def _report(
        self, access: AccessContext, report_id: UUID, number: int, *, write: bool = False
    ) -> tuple[ReportRecord, ReportVersion]:
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise InvalidRequest("Choose an exact positive report version.")
        report = await self.reports.get(report_id)
        if report is None:
            raise NotFound()
        access.require_read(report.created_by, report.team_id)
        if write:
            access.require_write(report.created_by, report.team_id)
        version = await self.reports.get_version(report_id, number)
        if version is None or version.report_id != report_id or version.number != number:
            raise NotFound()
        return report, version

    async def _claim(
        self,
        access: AccessContext,
        report: ReportRecord,
        version: ReportVersion,
        claim_id: UUID,
        revision_id: UUID,
        *,
        write: bool = False,
    ) -> tuple[ClaimRoot, ClaimRevision]:
        root = await self.claims.get(claim_id)
        if root is None:
            raise NotFound()
        access.require_read(root.created_by, root.team_id)
        if write:
            access.require_write(root.created_by, root.team_id)
        access.require_same_scope(root.created_by, root.team_id, report.created_by, report.team_id)
        if (
            root.report_id != report.id
            or root.report_version_id != version.id
            or root.report_version_number != version.number
            or root.evidence_sha256 != evidence_digest(version)
        ):
            raise Conflict("The claim is not anchored to this frozen report version.")
        revision = await self.claims.revision(root.id, revision_id)
        if revision is None:
            raise NotFound()
        if (
            revision.claim_id != root.id
            or revision.report_id != report.id
            or revision.report_version_id != version.id
        ):
            raise Conflict("Claim revision does not match the frozen report.")
        citations = tuple(
            ClaimCitationInput(
                row.label,
                row.relation,
                row.excerpt.field,
                row.excerpt.start,
                row.excerpt.end,
                row.excerpt.text,
            )
            for row in revision.citations
        )
        try:
            if freeze_claim_citations(version, citations) != revision.citations:
                raise ValueError("Frozen claim citation mismatch")
        except ValueError as exc:
            raise Conflict("Claim citations no longer match frozen evidence.") from exc
        return root, revision

    @staticmethod
    def _references(
        version: ReportVersion,
        revision: ClaimRevision,
        keys: tuple[CitationKey, ...],
        relation: ClaimRelation | None = None,
    ) -> tuple[PassageReference, ...]:
        allowed = {
            (row.label, row.excerpt.sha256)
            for row in revision.citations
            if relation is None or row.relation is relation
        }
        if len(keys) > 64 or len(set(keys)) != len(keys):
            raise InvalidRequest("Choose distinct, bounded frozen citation references.")
        if any((key.evidence_label, key.excerpt_sha256) not in allowed for key in keys):
            raise InvalidRequest("A citation does not match this exact claim revision.")
        return tuple(
            PassageReference(str(version.id), key.evidence_label, key.excerpt_sha256)
            for key in keys
        )

    async def _anchor(
        self,
        access: AccessContext,
        report: ReportRecord,
        version: ReportVersion,
        claim_id: UUID,
        revision_id: UUID,
    ) -> tuple[ReportLedgerAnchor, ClaimRevision]:
        root, revision = await self._claim(
            access, report, version, claim_id, revision_id, write=True
        )
        if revision.state is not ClaimReviewState.REVIEWED:
            raise InvalidRequest("Review this exact claim revision before creating a ledger.")
        ids, count = await self.ledgers.list_ids(version.id, 1, 0)
        del ids
        if count >= MAX_LEDGERS_PER_VERSION:
            raise InvalidRequest("This report version has reached its ledger limit.")
        return ReportLedgerAnchor(
            uuid4(),
            LedgerKind.FORECAST,
            report.id,
            version.id,
            root.id,
            revision.id,
            root.created_by,
            root.team_id,
            self.clock.now(),
            1,
        ), revision

    async def _existing(
        self,
        access: AccessContext,
        report_id: UUID,
        number: int,
        ledger_id: UUID,
        *,
        write: bool = False,
    ) -> tuple[ReportLedger, ClaimRevision]:
        report, version = await self._report(access, report_id, number, write=write)
        ledger = await self.ledgers.get(ledger_id)
        if (
            ledger is None
            or ledger.anchor.report_id != report_id
            or ledger.anchor.report_version_id != version.id
        ):
            raise NotFound()
        access.require_read(ledger.anchor.owner_id, ledger.anchor.team_id)
        if write:
            access.require_write(ledger.anchor.owner_id, ledger.anchor.team_id)
        root, revision = await self._claim(
            access,
            report,
            version,
            ledger.anchor.claim_id,
            ledger.anchor.claim_revision_id,
            write=write,
        )
        if (root.created_by, root.team_id) != (ledger.anchor.owner_id, ledger.anchor.team_id):
            raise Conflict("Ledger claim scope does not match its frozen anchor.")
        source_ref = ledger.anchor.source_reference
        if ledger.anchor.kind is LedgerKind.INDICATOR:
            if source_ref is None or source_ref.report_version_id != str(version.id):
                raise Conflict("Indicator source reference is missing or mis-scoped.")
            key = CitationKey(source_ref.evidence_id, source_ref.passage_id)
            if self._references(version, revision, (key,)) != (source_ref,):
                raise Conflict("Indicator source citation no longer matches its claim.")
        elif source_ref is not None:
            raise Conflict("Forecast ledger cannot retain an indicator source anchor.")
        return ledger, revision

    async def _commit(self, claims: AccessClaims) -> None:
        await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.uow.commit()

    async def _audit(
        self,
        action: AuditAction,
        access: AccessContext,
        ledger_id: UUID,
        context: RequestContext,
    ) -> None:
        await self.auditor.record(
            action,
            actor=access.actor.id,
            subject=str(ledger_id),
            ip=context.ip,
            details={"report_ledger_id": str(ledger_id)},
        )

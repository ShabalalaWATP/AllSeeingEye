"""Claim writes that participate in the caller's authorised report transaction."""

from dataclasses import replace

from ase.application.access import AccessContext
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports.claims import ClaimRepository
from ase.application.reports.automatic_claims import PendingAutomaticClaims
from ase.application.reports.claim_batch import claim_body_digest
from ase.application.reports.claims import MAX_SCOPE_BYTES, MAX_SCOPE_CLAIMS
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.audit import AuditAction
from ase.domain.claim_generation import ClaimGenerationReceipt, ClaimGenerationStatus
from ase.domain.claim_revisions import ClaimCitationInput, freeze_claim_citations
from ase.domain.errors import Conflict
from ase.domain.report_records import ReportRecord, ReportVersion


class AutomaticClaimStorage:
    """Caller holds the fresh administration/account guard until its final commit.

    Admission happens before report insertion so the exact outcome can be frozen in
    its analysis JSON. Writing follows report insertion in the same transaction.
    This helper deliberately neither commits nor swallows persistence failures.
    """

    def __init__(self, claims: ClaimRepository, auditor: Auditor) -> None:
        self.claims, self.auditor = claims, auditor

    @staticmethod
    def _validate(
        access: AccessContext,
        record: ReportRecord,
        version: ReportVersion,
        pending: PendingAutomaticClaims,
    ) -> None:
        access.require_write(record.created_by, record.team_id)
        if (
            access.actor.id != pending.actor_id
            or record.id != pending.report_id
            or version.report_id != record.id
            or version.id != pending.version_id
            or evidence_digest(version) != pending.evidence_sha256
            or claim_body_digest(version) != pending.body_sha256
        ):
            raise Conflict("Automatic claims no longer match the authorised report.")
        pending.receipt.validate()
        if pending.receipt.revision_ids != tuple(row.id for row in pending.revisions):
            raise Conflict("Automatic claim receipt and revisions disagree.")
        for row in pending.revisions:
            if (
                row.report_id != record.id
                or row.report_version_id != version.id
                or row.authored_by != access.actor.id
                or row.model_origin != pending.receipt.model_origin
            ):
                raise Conflict("Automatic claim identity does not match its report.")
            inputs = tuple(
                ClaimCitationInput(
                    item.label,
                    item.relation,
                    item.excerpt.field,
                    item.excerpt.start,
                    item.excerpt.end,
                    item.excerpt.text,
                )
                for item in row.citations
            )
            if freeze_claim_citations(version, inputs) != row.citations:
                raise Conflict("Automatic claim citations changed before saving.")

    async def admit(
        self,
        access: AccessContext,
        record: ReportRecord,
        version: ReportVersion,
        pending: PendingAutomaticClaims,
    ) -> PendingAutomaticClaims:
        self._validate(access, record, version, pending)
        if not pending.revisions:
            return pending
        count, size = await self.claims.scope_usage(record.created_by, record.team_id)
        total_bytes = sum(self.claims.storage_size(row) for row in pending.revisions)
        if (
            count + len(pending.revisions) > MAX_SCOPE_CLAIMS
            or size + total_bytes > MAX_SCOPE_BYTES
        ):
            return replace(
                pending,
                revisions=(),
                receipt=ClaimGenerationReceipt(
                    ClaimGenerationStatus.QUOTA_EXCEEDED,
                    model_origin=pending.receipt.model_origin,
                ),
            )
        return pending

    async def write(
        self,
        access: AccessContext,
        record: ReportRecord,
        version: ReportVersion,
        pending: PendingAutomaticClaims,
        context: RequestContext,
    ) -> None:
        self._validate(access, record, version, pending)
        for revision in pending.revisions:
            await self.claims.create(revision, pending.evidence_sha256)
            await self.auditor.record(
                AuditAction.CLAIM_CREATED,
                actor=access.actor.id,
                subject=str(revision.claim_id),
                ip=context.ip,
                details={
                    "report_id": str(record.id),
                    "revision_id": str(revision.id),
                    "number": revision.number,
                },
            )

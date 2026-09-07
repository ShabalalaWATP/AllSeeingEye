"""Authorised claim annotations preserve frozen reports and append correction history."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.claims import ClaimRepository
from ase.application.ports.reports import ReportRepository
from ase.application.reports.claim_batch import (
    ClaimBatchAnchor,
    build_proposal_batch,
    claim_body_digest,
)
from ase.application.reports.claim_proposals import ClaimProposal
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.audit import AuditAction
from ase.domain.claim_origin import ClaimModelOrigin
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimReviewState,
    ClaimRevision,
    freeze_claim_citations,
    revise_claim,
)
from ase.domain.claim_roots import ClaimRoot
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.report_records import ReportRecord, ReportVersion

MAX_SCOPE_CLAIMS = 1000
MAX_CLAIM_REVISIONS = 100
MAX_SCOPE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ClaimInput:
    statement: str
    kind: ClaimKind
    state: ClaimReviewState
    citations: tuple[ClaimCitationInput, ...]
    unresolved_conflicts: tuple[str, ...]
    reason: str


class ReportClaims:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        reports: ReportRepository,
        claims: ClaimRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports, self.claims = users, refresh_tokens, reports, claims
        self.access, self.clock, self.auditor, self.uow = access, clock, auditor, uow

    async def _context(self, claims: AccessClaims) -> AccessContext:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        return await self.access.context(actor)

    async def _report(self, access: AccessContext, report_id: UUID) -> ReportRecord:
        record = await self.reports.get(report_id)
        if record is None:
            raise NotFound()
        access.require_read(record.created_by, record.team_id)
        return record

    async def _version(self, report_id: UUID, number: int) -> ReportVersion:
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise InvalidRequest("Choose a positive report version.")
        version = await self.reports.get_version(report_id, number)
        if version is None or version.report_id != report_id or version.number != number:
            raise NotFound()
        return version

    async def _anchor(
        self, access: AccessContext, claim_id: UUID
    ) -> tuple[ClaimRoot, ReportVersion]:
        root = await self.claims.get(claim_id)
        if root is None:
            raise NotFound()
        access.require_read(root.created_by, root.team_id)
        report = await self._report(access, root.report_id)
        access.require_same_scope(root.created_by, root.team_id, report.created_by, report.team_id)
        version = await self._version(root.report_id, root.report_version_number)
        if version.id != root.report_version_id or evidence_digest(version) != root.evidence_sha256:
            raise Conflict("The frozen evidence anchor has changed.")
        return root, version

    async def _revision(
        self, root: ClaimRoot, version: ReportVersion, revision_id: UUID
    ) -> ClaimRevision:
        value = await self.claims.revision(root.id, revision_id)
        if value is None:
            raise NotFound()
        if value.report_id != root.report_id or value.report_version_id != root.report_version_id:
            raise Conflict("Claim revision does not match its frozen report anchor.")
        inputs = tuple(
            ClaimCitationInput(
                row.label,
                row.relation,
                row.excerpt.field,
                row.excerpt.start,
                row.excerpt.end,
                row.excerpt.text,
            )
            for row in value.citations
        )
        try:
            if freeze_claim_citations(version, inputs) != value.citations:
                raise ValueError("Frozen citation identity mismatch")
        except ValueError as exc:
            raise Conflict("Claim citations no longer match frozen evidence.") from exc
        return value

    async def list(
        self,
        claims: AccessClaims,
        report_id: UUID,
        version_number: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[tuple[ClaimRevision, ...], int]:
        if (
            type(limit) is not int
            or type(offset) is not int
            or not 1 <= limit <= 20
            or not 0 <= offset <= 1000
        ):
            raise InvalidRequest("Invalid claim page bounds.")
        access = await self._context(claims)
        report = await self._report(access, report_id)
        version = await self._version(report_id, version_number)
        digest = evidence_digest(version)
        ids, total = await self.claims.list_ids(
            access.visibility, report_id, version.id, limit, offset
        )
        values = []
        for claim_id in ids:
            root = await self.claims.get(claim_id)
            if root is None:
                raise NotFound()
            access.require_read(root.created_by, root.team_id)
            access.require_same_scope(
                root.created_by, root.team_id, report.created_by, report.team_id
            )
            if (
                root.report_id != report.id
                or root.report_version_id != version.id
                or root.report_version_number != version.number
                or root.evidence_sha256 != digest
            ):
                raise Conflict("The frozen evidence anchor has changed.")
            values.append(await self._revision(root, version, root.latest_revision_id))
        await self.uow.commit()
        return tuple(values), total

    async def get(
        self, claims: AccessClaims, claim_id: UUID, revision_id: UUID | None = None
    ) -> tuple[ClaimRoot, ClaimRevision]:
        access = await self._context(claims)
        root, version = await self._anchor(access, claim_id)
        value = await self._revision(root, version, revision_id or root.latest_revision_id)
        await self.uow.commit()
        return root, value

    def _build(
        self,
        version: ReportVersion,
        claim_id: UUID,
        previous: ClaimRevision | None,
        value: ClaimInput,
        actor_id: UUID,
    ) -> ClaimRevision:
        try:
            return revise_claim(
                version=version,
                revision_id=uuid4(),
                claim_id=claim_id,
                previous=previous,
                statement=value.statement,
                kind=value.kind,
                state=value.state,
                citations=value.citations,
                unresolved_conflicts=value.unresolved_conflicts,
                reason=value.reason,
                actor_id=actor_id,
                now=self.clock.now(),
            )
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc

    async def _quota(
        self, owner: UUID, team: UUID | None, value: ClaimRevision, *, creating: bool
    ) -> None:
        count, size = await self.claims.scope_usage(owner, team)
        if creating and count >= MAX_SCOPE_CLAIMS:
            raise InvalidRequest("This scope has reached its retained-claim limit.")
        if value.number > MAX_CLAIM_REVISIONS:
            raise InvalidRequest("This claim has reached its retained-revision limit.")
        if size + self.claims.storage_size(value) > MAX_SCOPE_BYTES:
            raise InvalidRequest("This scope has reached its claim storage limit.")

    async def create(
        self,
        claims: AccessClaims,
        report_id: UUID,
        version_number: int,
        value: ClaimInput,
        context: RequestContext,
    ) -> ClaimRevision:
        access = await self._context(claims)
        report = await self._report(access, report_id)
        access.require_create(report.team_id)
        version = await self._version(report.id, version_number)
        revision = self._build(version, uuid4(), None, value, access.actor.id)
        owner = report.created_by if report.team_id is None else access.actor.id
        await self._quota(owner, report.team_id, revision, creating=True)
        await self.claims.create(revision, evidence_digest(version))
        await self._audit(AuditAction.CLAIM_CREATED, access, revision, context)
        await self.uow.commit()
        return revision

    async def prepare_proposals(
        self, claims: AccessClaims, report_id: UUID, version_number: int
    ) -> ClaimBatchAnchor:
        """Check write admission, then release database guards before external work."""
        access = await self._context(claims)
        report = await self._report(access, report_id)
        access.require_create(report.team_id)
        version = await self._version(report.id, version_number)
        owner = report.created_by if report.team_id is None else access.actor.id
        count, size = await self.claims.scope_usage(owner, report.team_id)
        if count >= MAX_SCOPE_CLAIMS or size >= MAX_SCOPE_BYTES:
            raise InvalidRequest("This scope has reached its claim storage limit.")
        anchor = ClaimBatchAnchor(
            access.actor.id,
            report.created_by,
            report.team_id,
            report.id,
            version.id,
            version.number,
            claim_body_digest(version),
            version,
            evidence_digest(version),
        )
        await self.uow.commit()
        return anchor

    async def persist_proposals(
        self,
        claims: AccessClaims,
        anchor: ClaimBatchAnchor,
        proposals: tuple[ClaimProposal, ...],
        origin: ClaimModelOrigin,
        context: RequestContext,
    ) -> tuple[ClaimRevision, ...]:
        """Revalidate current authority and reserve capacity for the entire batch."""
        access = await self._context(claims)
        report = await self._report(access, anchor.report_id)
        access.require_create(report.team_id)
        version = await self._version(report.id, anchor.version_number)
        if (
            access.actor.id != anchor.actor_id
            or report.created_by != anchor.owner_id
            or report.team_id != anchor.team_id
            or version.id != anchor.version_id
            or evidence_digest(version) != anchor.evidence_sha256
            or claim_body_digest(version) != anchor.body_sha256
            or anchor.version.report_id != anchor.report_id
            or anchor.version.id != anchor.version_id
            or anchor.version.number != anchor.version_number
            or claim_body_digest(anchor.version) != anchor.body_sha256
            or evidence_digest(anchor.version) != anchor.evidence_sha256
        ):
            raise Conflict("The report or claim-generation scope has changed.")
        try:
            revisions = build_proposal_batch(
                version, proposals, origin, access.actor.id, self.clock.now()
            )
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        owner = report.created_by if report.team_id is None else access.actor.id
        count, size = await self.claims.scope_usage(owner, report.team_id)
        if count + len(revisions) > MAX_SCOPE_CLAIMS or (
            size + sum(self.claims.storage_size(item) for item in revisions) > MAX_SCOPE_BYTES
        ):
            raise InvalidRequest("This scope has insufficient claim capacity for the batch.")
        try:
            for revision in revisions:
                await self.claims.create(revision, anchor.evidence_sha256)
                await self._audit(AuditAction.CLAIM_CREATED, access, revision, context)
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return revisions

    async def update(
        self,
        claims: AccessClaims,
        claim_id: UUID,
        base_revision_id: UUID,
        value: ClaimInput,
        context: RequestContext,
    ) -> ClaimRevision:
        access = await self._context(claims)
        root, version = await self._anchor(access, claim_id)
        access.require_write(root.created_by, root.team_id)
        if root.latest_revision_id != base_revision_id:
            raise Conflict("This claim has a newer revision. Reload its history.")
        previous = await self._revision(root, version, base_revision_id)
        revision = self._build(version, root.id, previous, value, access.actor.id)
        await self._quota(root.created_by, root.team_id, revision, creating=False)
        if not await self.claims.append(revision, base_revision_id):
            await self.uow.rollback()
            raise Conflict()
        await self._audit(AuditAction.CLAIM_REVISED, access, revision, context)
        await self.uow.commit()
        return revision

    async def _audit(
        self,
        action: AuditAction,
        access: AccessContext,
        revision: ClaimRevision,
        context: RequestContext,
    ) -> None:
        await self.auditor.record(
            action,
            actor=access.actor.id,
            subject=str(revision.claim_id),
            ip=context.ip,
            details={
                "report_id": str(revision.report_id),
                "revision_id": str(revision.id),
                "number": revision.number,
            },
        )

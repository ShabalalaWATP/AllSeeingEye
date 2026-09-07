"""Current-authority identity review with immutable evidence and bounded history."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.identity_decisions import IdentityDecisionRepository
from ase.application.ports.reports import ReportRepository
from ase.application.reports.identity_integrity import identity_subject, validate_retained_identity
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.audit import AuditAction
from ase.domain.claim_revisions import ClaimCitationInput
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.identity_review import (
    IdentityDecisionRevision,
    IdentityDisposition,
    revise_identity_decision,
)
from ase.domain.identity_roots import IdentityDecisionRoot
from ase.domain.report_records import ReportRecord, ReportVersion

MAX_SCOPE_DECISIONS = 1000
MAX_SCOPE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class IdentityReviewInput:
    candidate_label: str
    disposition: IdentityDisposition
    rationale: str
    unresolved_conflicts: tuple[str, ...] = ()
    citations: tuple[ClaimCitationInput, ...] = ()


class ReportIdentities:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        reports: ReportRepository,
        identities: IdentityDecisionRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports = users, refresh_tokens, reports
        self.identities, self.access = identities, access
        self.clock, self.auditor, self.uow = clock, auditor, uow

    @asynccontextmanager
    async def _transaction(self, claims: AccessClaims) -> AsyncIterator[AccessContext]:
        try:
            await self.users.lock_administration()
            await self.users.lock_by_id(claims.user_id)
            actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
            yield await self.access.context(actor)
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def _report(self, access: AccessContext, report_id: UUID) -> ReportRecord:
        report = await self.reports.get(report_id)
        if report is None:
            raise NotFound()
        access.require_read(report.created_by, report.team_id)
        return report

    async def _version(self, report_id: UUID, number: int) -> ReportVersion:
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise InvalidRequest("Choose a positive report version.")
        version = await self.reports.get_version(report_id, number)
        if version is None or version.report_id != report_id or version.number != number:
            raise NotFound()
        return version

    async def _anchor(
        self, access: AccessContext, decision_id: UUID
    ) -> tuple[IdentityDecisionRoot, ReportVersion]:
        root = await self.identities.get(decision_id)
        if root is None:
            raise NotFound()
        access.require_read(root.created_by, root.team_id)
        report = await self._report(access, root.report_id)
        access.require_same_scope(root.created_by, root.team_id, report.created_by, report.team_id)
        version = await self._version(report.id, root.report_version_number)
        try:
            subject = identity_subject(report)
        except InvalidRequest as exc:
            raise Conflict("The identity review subject has changed.") from exc
        if (
            root.subject != subject
            or version.id != root.report_version_id
            or evidence_digest(version) != root.evidence_sha256
        ):
            raise Conflict("The identity review evidence or subject has changed.")
        return root, version

    async def _revision(
        self, root: IdentityDecisionRoot, version: ReportVersion, revision_id: UUID
    ) -> IdentityDecisionRevision:
        try:
            value = await self.identities.revision(root.id, revision_id)
        except ValueError as exc:
            raise Conflict("Identity history failed its integrity check.") from exc
        if value is None:
            raise NotFound()
        if value.id != revision_id:
            raise Conflict("Identity revision does not match the requested revision.")
        validate_retained_identity(root, version, value)
        return value

    async def get(
        self, claims: AccessClaims, decision_id: UUID, revision_id: UUID | None = None
    ) -> tuple[IdentityDecisionRoot, IdentityDecisionRevision]:
        async with self._transaction(claims) as access:
            root, version = await self._anchor(access, decision_id)
            value = await self._revision(root, version, revision_id or root.latest_revision_id)
        return root, value

    async def list(
        self,
        claims: AccessClaims,
        report_id: UUID,
        version_number: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[tuple[IdentityDecisionRevision, ...], int]:
        if (
            type(limit) is not int
            or type(offset) is not int
            or not 1 <= limit <= 20
            or not 0 <= offset <= MAX_SCOPE_DECISIONS
        ):
            raise InvalidRequest("Invalid identity review page bounds.")
        async with self._transaction(claims) as access:
            await self._report(access, report_id)
            version = await self._version(report_id, version_number)
            ids, total = await self.identities.list_ids(
                access.visibility, report_id, version.id, limit, offset
            )
            values = []
            for decision_id in ids:
                root, anchored = await self._anchor(access, decision_id)
                if root.report_id != report_id or anchored.id != version.id:
                    raise Conflict("Identity list contains an inconsistent report anchor.")
                values.append(await self._revision(root, anchored, root.latest_revision_id))
        return tuple(values), total

    def _build(
        self,
        report: ReportRecord,
        version: ReportVersion,
        decision_id: UUID,
        previous: IdentityDecisionRevision | None,
        value: IdentityReviewInput,
        actor: UUID,
    ) -> IdentityDecisionRevision:
        try:
            return revise_identity_decision(
                version=version,
                revision_id=uuid4(),
                decision_id=decision_id,
                previous=previous,
                subject=identity_subject(report),
                candidate_label=value.candidate_label,
                disposition=value.disposition,
                rationale=value.rationale,
                unresolved_conflicts=value.unresolved_conflicts,
                citations=value.citations,
                actor_id=actor,
                now=self.clock.now(),
            )
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc

    async def _quota(
        self, owner: UUID, team: UUID | None, revision: IdentityDecisionRevision, *, creating: bool
    ) -> None:
        count, size = await self.identities.scope_usage(owner, team)
        if creating and count >= MAX_SCOPE_DECISIONS:
            raise InvalidRequest("This scope has reached its identity review limit.")
        if size + self.identities.storage_size(revision) > MAX_SCOPE_BYTES:
            raise InvalidRequest("This scope has reached its identity storage limit.")

    async def create(
        self,
        claims: AccessClaims,
        report_id: UUID,
        version_number: int,
        value: IdentityReviewInput,
        context: RequestContext,
    ) -> IdentityDecisionRevision:
        async with self._transaction(claims) as access:
            report = await self._report(access, report_id)
            access.require_create(report.team_id)
            version = await self._version(report_id, version_number)
            revision = self._build(report, version, uuid4(), None, value, access.actor.id)
            if await self.identities.candidate_id(version.id, value.candidate_label) is not None:
                raise Conflict("This candidate already has a review. Open its history.")
            owner = report.created_by if report.team_id is None else access.actor.id
            await self._quota(owner, report.team_id, revision, creating=True)
            await self.identities.create(revision, evidence_digest(version))
            await self._audit(AuditAction.IDENTITY_CREATED, access, revision, context)
        return revision

    async def update(
        self,
        claims: AccessClaims,
        decision_id: UUID,
        base_revision_id: UUID,
        value: IdentityReviewInput,
        context: RequestContext,
    ) -> IdentityDecisionRevision:
        async with self._transaction(claims) as access:
            root, version = await self._anchor(access, decision_id)
            access.require_write(root.created_by, root.team_id)
            if root.latest_revision_id != base_revision_id:
                raise Conflict("This identity review has a newer revision. Reload its history.")
            previous = await self._revision(root, version, base_revision_id)
            report = await self._report(access, root.report_id)
            revision = self._build(report, version, root.id, previous, value, access.actor.id)
            await self._quota(root.created_by, root.team_id, revision, creating=False)
            if not await self.identities.append(revision, base_revision_id):
                raise Conflict("This identity review changed during correction.")
            await self._audit(AuditAction.IDENTITY_REVISED, access, revision, context)
        return revision

    async def _audit(
        self,
        action: AuditAction,
        access: AccessContext,
        value: IdentityDecisionRevision,
        context: RequestContext,
    ) -> None:
        await self.auditor.record(
            action,
            actor=access.actor.id,
            subject=str(value.decision_id),
            ip=context.ip,
            details={
                "report_id": str(value.report_id),
                "revision_id": str(value.id),
                "number": value.number,
            },
        )

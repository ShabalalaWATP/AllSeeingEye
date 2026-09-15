"""Authorised reviewer decisions and immutable source assessment snapshots."""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.source_reviews import SourceReviewRepository
from ase.application.reports.source_review_projection import freeze_reviewed_sources, review_target
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.events import Credibility, Reliability
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.source_assessment import (
    ASSESSMENT_POLICY_VERSION,
    Assessor,
    Authenticity,
    IssuerAuthenticity,
    RatingReview,
    RatingStatus,
)
from ase.domain.source_assessment_bindings import assert_source_assessment_matches
from ase.domain.source_review_records import SourceReviewSnapshot, encode_source_review
from ase.domain.source_reviews import (
    MAX_SCOPE_REVIEW_BYTES,
    MAX_SCOPE_REVIEW_HEADS,
    MAX_VERSION_SOURCE_SNAPSHOTS,
    SourceReviewKind,
    SourceReviewRevision,
    SourceReviewScope,
    source_review_key,
)


@dataclass(frozen=True, slots=True)
class SourceReviewInput:
    label: str
    judgement_id: str
    subject: str
    kind: SourceReviewKind
    basis: str
    previous_id: UUID | None = None
    reliability: Reliability | None = None
    expertise_basis: str | None = None
    credibility: Credibility | None = None
    authenticity: Authenticity | None = None
    policy_note: str | None = None


class ReportSourceReviews:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        reports: ReportRepository,
        reviews: SourceReviewRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports, self.reviews = users, refresh, reports, reviews
        self.access, self.clock, self.auditor, self.uow = access, clock, auditor, uow

    async def _context(self, claims: AccessClaims) -> AccessContext:
        # All work is local. Hold the existing identity/membership guard through commit.
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        return await self.access.context(actor)

    async def _version(
        self, access: AccessContext, report_id: UUID, number: int, *, write: bool = False
    ) -> tuple[ReportRecord, ReportVersion]:
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise InvalidRequest("Choose an exact positive report version.")
        record = await self.reports.get(report_id)
        if record is None:
            raise NotFound()
        access.require_read(record.created_by, record.team_id)
        if write:
            access.require_write(record.created_by, record.team_id)
        version = await self.reports.get_version(report_id, number)
        if version is None or version.report_id != report_id or version.number != number:
            raise NotFound()
        return record, version

    async def history(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        label: str,
        judgement_id: str,
        subject: str,
        kind: SourceReviewKind,
    ) -> tuple[SourceReviewRevision, ...]:
        access = await self._context(claims)
        record, version = await self._version(access, report_id, number)
        try:
            target = review_target(version, label, judgement_id, subject)
        except ValueError as exc:
            raise InvalidRequest("The review target does not match cited frozen evidence.") from exc
        scope = SourceReviewScope(record.created_by, record.team_id)
        history = await self.reviews.history(scope, source_review_key(scope, kind, target))
        if history:
            access.require_read(history[0].scope.owner_id, history[0].scope.team_id)
        await self._commit(claims)
        return history

    async def review(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        value: SourceReviewInput,
        context: RequestContext,
    ) -> SourceReviewRevision:
        access = await self._context(claims)
        record, version = await self._version(access, report_id, number, write=True)
        scope = SourceReviewScope(record.created_by, record.team_id)
        try:
            target = review_target(version, value.label, value.judgement_id, value.subject)
            history = await self.reviews.history(
                scope, source_review_key(scope, value.kind, target)
            )
            if history:
                scope = history[0].scope
                access.require_write(scope.owner_id, scope.team_id)
            elif record.team_id is not None:
                scope = SourceReviewScope(access.actor.id, record.team_id)
            if (history[-1].review.id if history else None) != (
                str(value.previous_id) if value.previous_id else None
            ):
                raise Conflict("This source assessment has a newer revision. Reload its history.")
            now = self.clock.now()
            review = RatingReview(
                str(uuid4()),
                Assessor.REVIEWER,
                str(access.actor.id),
                RatingStatus.APPLIED,
                value.basis,
                ASSESSMENT_POLICY_VERSION,
                now,
                now,
                str(value.previous_id) if value.previous_id else None,
                value.policy_note,
            )
            authenticity = (
                IssuerAuthenticity(
                    target.capture_id,
                    target.source_id,
                    value.authenticity,
                    value.basis,
                    f"report:{version.id}:capture:{target.capture_id}",
                )
                if value.authenticity is not None
                else None
            )
            revision = SourceReviewRevision(
                scope,
                target,
                value.kind,
                len(history) + 1,
                review,
                value.reliability,
                value.expertise_basis,
                value.credibility,
                authenticity,
            )
            count, size = await self.reviews.scope_usage(scope)
            if (not history and count >= MAX_SCOPE_REVIEW_HEADS) or size + encode_source_review(
                revision
            )[2] > MAX_SCOPE_REVIEW_BYTES:
                raise InvalidRequest("This scope has reached its retained source-review limit.")
        except ValueError as exc:
            raise InvalidRequest("Invalid scoped source assessment or review history.") from exc
        if not await self.reviews.append(revision):
            await self.uow.rollback()
            raise Conflict("This source assessment has a newer revision. Reload its history.")
        await self._audit(
            AuditAction.SOURCE_RATING_REVIEWED, access, revision.review.id, report_id, context
        )
        await self._commit(claims)
        return revision

    async def freeze(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        subjects: Mapping[str, str],
        context: RequestContext,
    ) -> SourceReviewSnapshot:
        access = await self._context(claims)
        record, version = await self._version(access, report_id, number, write=True)
        if await self.reviews.snapshot_count(version.id) >= MAX_VERSION_SOURCE_SNAPSHOTS:
            raise InvalidRequest("This report version has reached its source-snapshot limit.")
        try:
            snapshot = await freeze_reviewed_sources(
                self.reviews,
                version,
                SourceReviewScope(record.created_by, record.team_id),
                access.actor.id,
                subjects,
                self.clock.now(),
            )
            await self.reviews.add_snapshot(snapshot)
        except ValueError as exc:
            raise InvalidRequest(
                "This saved report cannot support the requested scoped source snapshot."
            ) from exc
        await self._audit(
            AuditAction.SOURCE_ASSESSMENT_FROZEN, access, str(snapshot.id), report_id, context
        )
        await self._commit(claims)
        return snapshot

    async def snapshot(
        self, claims: AccessClaims, report_id: UUID, number: int, snapshot_id: UUID
    ) -> SourceReviewSnapshot:
        access = await self._context(claims)
        record, version = await self._version(access, report_id, number)
        snapshot = await self.reviews.snapshot(snapshot_id)
        if (
            snapshot is None
            or snapshot.report_id != report_id
            or snapshot.report_version_id != version.id
        ):
            raise NotFound()
        access.require_read(snapshot.scope.owner_id, snapshot.scope.team_id)
        access.require_same_scope(
            snapshot.scope.owner_id, snapshot.scope.team_id, record.created_by, record.team_id
        )
        assert_source_assessment_matches(
            snapshot.projection,
            report_version_id=version.id,
            body=version.body,
            evidence=version.evidence,
        )
        await self._commit(claims)
        return snapshot

    async def _commit(self, claims: AccessClaims) -> None:
        await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.uow.commit()

    async def _audit(
        self,
        action: AuditAction,
        access: AccessContext,
        identifier: str,
        report_id: UUID,
        context: RequestContext,
    ) -> None:
        await self.auditor.record(
            action,
            actor=access.actor.id,
            subject=identifier,
            ip=context.ip,
            details={"report_id": str(report_id)},
        )

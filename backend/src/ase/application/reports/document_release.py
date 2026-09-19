"""Exact rendered-document authority, held until HTTP response session teardown."""

from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.source_reviews import SourceReviewRepository
from ase.application.reports.reviewed_source_document import validate_reviewed_snapshot
from ase.domain.errors import Conflict, NotFound, Unauthenticated
from ase.domain.report_documents import ReportFile


async def release_document(
    claims: AccessClaims,
    report_id: UUID,
    rendered: ReportFile,
    *,
    users: UserRepository,
    refresh: RefreshTokenRepository,
    reports: ReportRepository,
    access: AccessPolicy,
    clock: Clock,
    uow: UnitOfWork,
    source_reviews: SourceReviewRepository | None = None,
    source_snapshot_id: UUID | None = None,
) -> None:
    if rendered.report_version_id is None or rendered.version_number is None:
        raise Conflict("The rendered document has no exact report version.")
    await release_report_view(
        claims,
        report_id,
        rendered.version_number,
        rendered.report_version_id,
        users=users,
        refresh=refresh,
        reports=reports,
        access=access,
        clock=clock,
        uow=uow,
        source_reviews=source_reviews,
        source_snapshot_id=source_snapshot_id,
    )


async def release_report_view(
    claims: AccessClaims,
    report_id: UUID,
    version_number: int,
    report_version_id: UUID,
    *,
    users: UserRepository,
    refresh: RefreshTokenRepository,
    reports: ReportRepository,
    access: AccessPolicy,
    clock: Clock,
    uow: UnitOfWork,
    source_reviews: SourceReviewRepository | None = None,
    source_snapshot_id: UUID | None = None,
) -> None:
    """Recheck the exact private report projection immediately before release."""
    # End any renderer read snapshot before taking the same SQL administration
    # guard used by report deletion and membership/account mutations. No lock
    # spans rendering. Successful release leaves this transaction open until
    # request teardown, rather than awaiting a commit/close before HTTP return.
    await uow.rollback()
    await users.lock_administration()
    actor = await validate_current_session(claims, users, refresh, clock)
    context = await access.context(actor, for_update=True)
    record = await reports.get(report_id)
    if record is None:
        raise NotFound()
    context.require_read(record.created_by, record.team_id)
    version = await reports.get_version(report_id, version_number)
    if version is None:
        raise NotFound()
    if version.id != report_version_id:
        raise Conflict("The rendered document's exact report version changed.")
    if source_snapshot_id is not None:
        if source_reviews is None:
            raise Conflict("The reviewed source snapshot cannot be rechecked.")
        snapshot = await source_reviews.snapshot(source_snapshot_id)
        if (
            snapshot is None
            or snapshot.report_id != report_id
            or snapshot.report_version_id != version.id
        ):
            raise NotFound()
        context.require_read(snapshot.scope.owner_id, snapshot.scope.team_id)
        context.require_same_scope(
            snapshot.scope.owner_id,
            snapshot.scope.team_id,
            record.created_by,
            record.team_id,
        )
        validate_reviewed_snapshot(record, version, snapshot)
    # Logout is independent of the administration guard. Check its current
    # committed family state after all object reads, then check time synchronously.
    await validate_current_session(claims, users, refresh, clock)
    if claims.expires_at <= clock.now():
        raise Unauthenticated("The session has ended. Sign in again.")

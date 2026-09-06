"""Parent-scoped saved views with immutable revisions and locked retention quotas."""

from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.map_views import MapViewRepository
from ase.application.ports.reports import ReportRepository
from ase.application.research.map_view_evidence import evidence_digest, validate_selection
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.map_view_records import revision_bytes, revision_digest
from ase.domain.map_views import (
    MAX_SCOPE_REVISION_BYTES,
    MAX_SCOPE_VIEWS,
    MAX_VIEW_REVISIONS,
    MapView,
    MapViewPage,
    MapViewRevision,
    MapViewState,
    bounded_text,
)
from ase.domain.report_records import ReportRecord, ReportVersion


class SavedMapViews:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        reports: ReportRepository,
        views: MapViewRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports, self.views = users, refresh_tokens, reports, views
        self.access, self.clock, self.auditor, self.uow = access, clock, auditor, uow

    async def _context(self, claims: AccessClaims) -> AccessContext:
        # Serialises scope/quota decisions with account and membership transitions.
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
        if type(number) is not int or number < 1:
            raise InvalidRequest("Choose a positive report version.")
        version = await self.reports.get_version(report_id, number)
        if version is None:
            raise NotFound()
        return version

    async def _view(self, access: AccessContext, view_id: UUID) -> tuple[MapView, ReportRecord]:
        view = await self.views.get(view_id)
        if view is None:
            raise NotFound()
        access.require_read(view.created_by, view.team_id)
        report = await self._report(access, view.report_id)
        access.require_same_scope(view.created_by, view.team_id, report.created_by, report.team_id)
        return view, report

    async def list(
        self,
        claims: AccessClaims,
        report_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> MapViewPage:
        if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise InvalidRequest("Invalid map view page bounds.")
        access = await self._context(claims)
        await self._report(access, report_id)
        page = await self.views.list_visible(access.visibility, report_id, limit, offset)
        await self.uow.commit()
        return page

    async def get(
        self,
        claims: AccessClaims,
        view_id: UUID,
        revision_id: UUID | None = None,
    ) -> tuple[MapView, MapViewRevision]:
        access = await self._context(claims)
        view, _ = await self._view(access, view_id)
        revision = await self.views.revision(view.id, revision_id or view.latest_revision_id)
        if revision is None:
            raise NotFound()
        version = await self._version(view.report_id, revision.report_version_number)
        if version.id != revision.report_version_id:
            raise NotFound()
        if evidence_digest(version) != revision.evidence_sha256:
            raise Conflict("The saved evidence anchor has changed; this view cannot be reproduced.")
        if (
            revision_digest(
                revision.state, revision.title, str(version.id), revision.evidence_sha256
            )
            != revision.content_sha256
        ):
            raise Conflict("The saved view failed its content integrity check.")
        await self.uow.commit()
        return view, revision

    async def _quota(self, view: MapView, revision: MapViewRevision, *, creating: bool) -> None:
        count, size = await self.views.scope_usage(view.created_by, view.team_id)
        if creating and count >= MAX_SCOPE_VIEWS:
            raise InvalidRequest("This personal/team scope has reached its saved-map limit.")
        if revision.number > MAX_VIEW_REVISIONS:
            raise InvalidRequest("This map view has reached its retained-revision limit.")
        if size + revision_bytes(revision.state, revision.title) > MAX_SCOPE_REVISION_BYTES:
            raise InvalidRequest("This personal/team scope has reached its map storage limit.")

    def _revision(
        self,
        actor_id: UUID,
        view_id: UUID,
        number: int,
        version: ReportVersion,
        title: str,
        state: MapViewState,
    ) -> MapViewRevision:
        try:
            bounded_text(title, 200, "view title")
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        validate_selection(state, version)
        digest = evidence_digest(version)
        return MapViewRevision(
            uuid4(),
            view_id,
            number,
            title,
            version.id,
            version.number,
            state,
            digest,
            revision_digest(state, title, str(version.id), digest),
            actor_id,
            self.clock.now(),
        )

    async def create(
        self,
        claims: AccessClaims,
        report_id: UUID,
        version_number: int,
        title: str,
        state: MapViewState,
        context: RequestContext,
    ) -> tuple[MapView, MapViewRevision]:
        access = await self._context(claims)
        report = await self._report(access, report_id)
        access.require_create(report.team_id)
        version = await self._version(report.id, version_number)
        view_id = uuid4()
        revision = self._revision(access.actor.id, view_id, 1, version, title, state)
        # A personal map belongs to its parent owner even when an admin creates it.
        owner = report.created_by if report.team_id is None else access.actor.id
        view = MapView(view_id, report.id, owner, report.team_id, revision.id, self.clock.now())
        await self._quota(view, revision, creating=True)
        await self.views.create(view, revision)
        await self._audit(AuditAction.MAP_VIEW_CREATED, access, view, context)
        await self.uow.commit()
        return view, revision

    async def update(
        self,
        claims: AccessClaims,
        view_id: UUID,
        base_revision_id: UUID,
        version_number: int,
        title: str,
        state: MapViewState,
        context: RequestContext,
    ) -> tuple[MapView, MapViewRevision]:
        access = await self._context(claims)
        view, report = await self._view(access, view_id)
        access.require_write(view.created_by, view.team_id)
        if view.archived or view.latest_revision_id != base_revision_id:
            raise Conflict()
        previous = await self.views.revision(view.id, base_revision_id)
        if previous is None:
            raise NotFound()
        version = await self._version(report.id, version_number)
        revision = self._revision(
            access.actor.id, view.id, previous.number + 1, version, title, state
        )
        await self._quota(view, revision, creating=False)
        if not await self.views.append(revision, base_revision_id):
            await self.uow.rollback()
            raise Conflict()
        await self._audit(AuditAction.MAP_VIEW_REVISED, access, view, context)
        await self.uow.commit()
        return replace(view, latest_revision_id=revision.id), revision

    async def archive(self, claims: AccessClaims, view_id: UUID, context: RequestContext) -> None:
        access = await self._context(claims)
        view, _ = await self._view(access, view_id)
        access.require_write(view.created_by, view.team_id)
        await self.views.archive(view.id)
        await self._audit(AuditAction.MAP_VIEW_ARCHIVED, access, view, context)
        await self.uow.commit()

    async def _audit(
        self,
        action: AuditAction,
        access: AccessContext,
        view: MapView,
        context: RequestContext,
    ) -> None:
        await self.auditor.record(
            action,
            actor=access.actor.id,
            subject=str(view.id),
            ip=context.ip,
            details={"report_id": str(view.report_id)},
        )

"""Typed board subjects, checked against current access when written and when read.

A post may name one team report version, saved area or drawing collection. The
subject must share the post's team on write. Every read resolves it again, so a
subject that has moved, been deleted or become unreadable shows as unavailable and
never discloses its title. The board stays separate from evidence: a subject is a
pointer for discussion, never copied into a report.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ase.application.access import AccessContext, AccessPolicy
from ase.application.ports.direction import AoiRepository
from ase.application.ports.map_workspace import MapWorkspaceRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.team_board import TeamBoardRepository
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.team_board import (
    BoardSubject,
    BoardSubjectKind,
    BoardSubjectView,
    ReportDiscussion,
    TeamBoardPost,
)
from ase.domain.users import User

UNAVAILABLE = "The linked item is not available."
OTHER_SCOPE = "A board post can only link work that belongs to this team."


@dataclass(frozen=True, slots=True)
class _Scoped:
    created_by: UUID
    team_id: UUID | None
    title: str


class BoardSubjects:
    def __init__(
        self,
        access: AccessPolicy,
        reports: ReportRepository,
        areas: AoiRepository,
        documents: MapWorkspaceRepository,
    ) -> None:
        self._access = access
        self._reports = reports
        self._areas = areas
        self._documents = documents

    async def context(self, actor: User) -> AccessContext:
        return await self._access.context(actor)

    async def _scope(self, subject: BoardSubject) -> _Scoped | None:
        if subject.kind is BoardSubjectKind.REPORT_VERSION:
            report = await self._reports.get(subject.id)
            # Versions are immutable and only removed with their report.
            if report is None or (subject.version or 0) > report.latest_version:
                return None
            return _Scoped(report.created_by, report.team_id, report.title)
        if subject.kind is BoardSubjectKind.SAVED_AREA:
            area = await self._areas.get(subject.id)
            return _Scoped(area.created_by, area.team_id, area.name) if area else None
        document = await self._documents.get(subject.id)
        if document is None or document.kind != "drawings":
            return None
        return _Scoped(document.created_by, document.team_id, document.title)

    async def require_linkable(
        self, context: AccessContext, team_id: UUID, subject: BoardSubject
    ) -> BoardSubjectView:
        """Refuse missing, unreadable, personal and other-team subjects, even for admins."""
        scoped = await self._scope(subject)
        if scoped is None:
            raise InvalidRequest(UNAVAILABLE)
        try:
            context.require_same_scope(context.actor.id, team_id, scoped.created_by, scoped.team_id)
        except NotFound:
            # The same answer as a missing subject, so existence is not confirmed.
            raise InvalidRequest(UNAVAILABLE) from None
        except InvalidRequest:
            raise InvalidRequest(OTHER_SCOPE) from None
        return BoardSubjectView(subject, scoped.title)

    async def view(self, context: AccessContext, post: TeamBoardPost) -> BoardSubjectView | None:
        """The subject as this reader may see it now; removed posts show none."""
        if post.subject is None or post.deleted_at is not None:
            return None
        scoped = await self._scope(post.subject)
        if scoped is None:
            return BoardSubjectView.unavailable(post.subject)
        try:
            context.require_same_scope(
                post.author_id, post.team_id, scoped.created_by, scoped.team_id
            )
        except (NotFound, InvalidRequest):
            return BoardSubjectView.unavailable(post.subject)
        return BoardSubjectView(post.subject, scoped.title)


class ReportDiscussions:
    """Live board threads about one report, for any reader of that report."""

    def __init__(
        self, access: AccessPolicy, reports: ReportRepository, board: TeamBoardRepository
    ) -> None:
        self._access = access
        self._reports = reports
        self._board = board

    async def for_report(self, actor: User, report_id: UUID) -> ReportDiscussion:
        context = await self._access.context(actor)
        report = await self._reports.get(report_id)
        if report is None:
            raise NotFound()
        context.require_read(report.created_by, report.team_id)
        if report.team_id is None:
            return ReportDiscussion(None, 0, None, can_post=False)
        team = context.teams.get(report.team_id)
        count, latest = await self._board.subject_threads(
            report.team_id, BoardSubjectKind.REPORT_VERSION, report.id
        )
        can_post = team is not None and team.is_active
        can_post = can_post and (context.actor.is_admin or report.team_id in context.memberships)
        return ReportDiscussion(report.team_id, count, latest, can_post=can_post)

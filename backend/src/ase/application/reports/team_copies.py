"""Copy one finished personal report version into a team, without another model run.

Only the version's owner may copy it, into an active team they currently belong to,
including administrators: publication widens access to personal work, so there is no
administrator override. Private-input evidence is published only after the caller
confirms the exact listed labels. Access is checked again under the administration
guard immediately before the copy, its provenance and the audit entry are committed
together; a retry or a concurrent request returns the existing copy.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.report_team_copies import ReportTeamCopyRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.repositories import UserRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.report_team_copy import (
    LinkedArtefacts,
    ReportTeamCopy,
    TeamCopyPlan,
    copy_for_team,
    plan_team_copy,
)
from ase.domain.reports import ReportStatus
from ase.domain.teams import Team
from ase.domain.users import User

MAX_DISCLOSED_LABELS = 200


@dataclass(frozen=True, slots=True)
class TeamCopyPreview:
    team: Team
    source_version_number: int
    plan: TeamCopyPlan
    linked: LinkedArtefacts
    existing: ReportTeamCopy | None


@dataclass(frozen=True, slots=True)
class TeamCopyResult:
    copy: ReportTeamCopy
    created: bool


@dataclass(frozen=True, slots=True)
class TeamCopyProvenance:
    copy: ReportTeamCopy
    copied_by_name: str | None
    source_visible: bool


def _authorise(
    access: AccessContext, record: ReportRecord, version: ReportVersion | None, team_id: UUID
) -> tuple[ReportVersion, Team]:
    access.require_read(record.created_by, record.team_id)
    if record.team_id is not None:
        raise InvalidRequest("Only a personal report version can be copied to a team.")
    if record.created_by != access.actor.id:
        raise Forbidden("Only the report's owner can copy it to a team.")
    if version is None:
        raise NotFound()
    if version.status is ReportStatus.FAILED:
        raise InvalidRequest("Only a finished report version can be copied to a team.")
    team = access.teams.get(team_id)
    if team is None:
        raise NotFound()
    if team_id not in access.memberships:
        raise Forbidden("Copy reports only to a team you currently belong to.")
    if not team.is_active:
        raise Forbidden("Archived teams are read-only.")
    return version, team


def _require_disclosure(plan: TeamCopyPlan, disclosed: Sequence[str]) -> None:
    listed = {row.label for row in plan.private_inputs}
    if len(disclosed) > MAX_DISCLOSED_LABELS or set(disclosed) != listed:
        raise InvalidRequest(
            "Confirm exactly the listed private-input evidence before copying to the team.",
            fields={"disclosed_evidence_labels": "Confirm the current disclosure list."},
        )


class ReportTeamCopies:
    def __init__(
        self,
        reports: ReportRepository,
        copies: ReportTeamCopyRepository,
        users: UserRepository,
        access: AccessPolicy,
        auditor: Auditor,
        uow: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._reports, self._copies, self._users = reports, copies, users
        self._access, self._auditor, self._uow, self._clock = access, auditor, uow, clock

    async def _load(
        self, access: AccessContext, report_id: UUID, number: int, team_id: UUID
    ) -> tuple[ReportRecord, ReportVersion, Team]:
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        version, team = _authorise(
            access, record, await self._reports.get_version(report_id, number), team_id
        )
        return record, version, team

    async def preview(
        self, actor: User, report_id: UUID, number: int, team_id: UUID
    ) -> TeamCopyPreview:
        access = await self._access.context(actor)
        record, version, team = await self._load(access, report_id, number, team_id)
        return TeamCopyPreview(
            team,
            version.number,
            plan_team_copy(record, version),
            await self._copies.linked_artefacts(version.id),
            await self._copies.find(version.id, team_id),
        )

    async def copy(
        self,
        actor: User,
        report_id: UUID,
        number: int,
        team_id: UUID,
        disclosed: Sequence[str],
        context: RequestContext,
        before_save: Callable[[], Awaitable[None]],
    ) -> TeamCopyResult:
        access = await self._access.context(actor)
        record, version, _ = await self._load(access, report_id, number, team_id)
        plan = plan_team_copy(record, version)
        _require_disclosure(plan, disclosed)
        existing = await self._copies.find(version.id, team_id)
        if existing is not None:
            return TeamCopyResult(existing, created=False)
        # End the read snapshot, confirm the session, then decide again under the guard
        # that membership, archive and account changes also take.
        await self._uow.rollback()
        await before_save()
        access = await self._access.context(actor, for_update=True)
        record, version, _ = await self._load(access, report_id, number, team_id)
        current = plan_team_copy(record, version)
        if current != plan:
            raise Conflict("The report changed. Review the disclosure again before copying.")
        existing = await self._copies.find(version.id, team_id)
        if existing is not None:
            return TeamCopyResult(existing, created=False)
        return await self._persist(actor, record, version, team_id, plan, disclosed, context)

    async def _persist(
        self,
        actor: User,
        record: ReportRecord,
        version: ReportVersion,
        team_id: UUID,
        plan: TeamCopyPlan,
        disclosed: Sequence[str],
        context: RequestContext,
    ) -> TeamCopyResult:
        now = self._clock.now()
        team_record, team_version = copy_for_team(
            record,
            version,
            report_id=uuid4(),
            version_id=uuid4(),
            team_id=team_id,
            copied_by=actor.id,
            now=now,
        )
        copy = ReportTeamCopy(
            id=uuid4(),
            report_id=team_record.id,
            team_id=team_id,
            source_report_id=record.id,
            source_version_id=version.id,
            source_version_number=version.number,
            copied_by=actor.id,
            copied_at=now,
            content_sha256=plan.content_sha256,
            disclosed_labels=tuple(sorted(set(disclosed))),
            omissions=plan.omissions,
        )
        try:
            await self._reports.add(team_record, team_version)
            await self._copies.add(copy)
        except Conflict:
            # A concurrent request committed the same copy first: nothing of ours remains.
            await self._uow.rollback()
            existing = await self._copies.find(version.id, team_id)
            if existing is None:
                raise
            return TeamCopyResult(existing, created=False)
        await self._auditor.record(
            AuditAction.REPORT_COPIED_TO_TEAM,
            actor=actor.id,
            subject=str(team_record.id),
            ip=context.ip,
            details={
                "source_report_id": str(record.id),
                "source_version": version.number,
                "team_id": str(team_id),
                "disclosed_private_inputs": len(copy.disclosed_labels),
                "omissions": [value.value for value in plan.omissions],
                "content_sha256": plan.content_sha256,
            },
        )
        await self._uow.commit()
        return TeamCopyResult(copy, created=True)

    async def provenance(self, actor: User, report_id: UUID) -> TeamCopyProvenance:
        """Who copied this team report and from which version, for its current readers."""
        access = await self._access.context(actor)
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        access.require_read(record.created_by, record.team_id)
        copy = await self._copies.for_report(report_id)
        if copy is None:
            raise NotFound()
        user = await self._users.get_by_id(copy.copied_by)
        # The personal original stays private: only its owner or an administrator
        # learns its identity, and nobody receives a link that reaches it otherwise.
        visible = access.actor.is_admin or access.actor.id == copy.copied_by
        return TeamCopyProvenance(copy, user.display_name if user else None, visible)

"""Record, read and export human citation verdicts under current report authority.

Reading needs current read access to the report. Recording also needs the existing
write authority for the report's personal or team scope: the personal owner, a current
member of an active team, or an administrator under the documented manual override.
Archived-team read access alone does not permit a verdict. Verdicts never touch the
frozen report version.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.citation_verdicts import CitationVerdictRepository
from ase.application.ports.reports import ReportRepository
from ase.domain.audit import AuditAction
from ase.domain.citation_verdict_export import encode_verdict_export
from ase.domain.citation_verdicts import (
    MAX_CITATION_VERDICTS,
    MAX_VERSION_VERDICTS,
    CitationVerdict,
    CitationVerdictValue,
    cited_anchor,
)
from ase.domain.errors import AppError, InvalidRequest, NotFound
from ase.domain.report_records import ReportRecord, ReportVersion


@dataclass(frozen=True, slots=True)
class CitationVerdictInput:
    judgement_id: str
    label: str
    relation: str
    verdict: CitationVerdictValue
    note: str | None = None


@dataclass(frozen=True, slots=True)
class CitationVerdictList:
    verdicts: tuple[CitationVerdict, ...]
    can_record: bool
    limit: int


@dataclass(frozen=True, slots=True)
class CitationVerdictExport:
    filename: str
    content: bytes


class CitationVerdicts:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        reports: ReportRepository,
        verdicts: CitationVerdictRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports, self.verdicts = users, refresh, reports, verdicts
        self.access, self.clock, self.auditor, self.uow = access, clock, auditor, uow

    async def _read_context(self, claims: AccessClaims) -> AccessContext:
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        return await self.access.context(actor)

    async def _version(
        self, access: AccessContext, report_id: UUID, number: int
    ) -> tuple[ReportRecord, ReportVersion]:
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise InvalidRequest("Choose an exact positive report version.")
        record = await self.reports.get(report_id)
        if record is None:
            raise NotFound()
        access.require_read(record.created_by, record.team_id)
        version = await self.reports.get_version(report_id, number)
        if version is None or version.report_id != report_id or version.number != number:
            raise NotFound()
        return record, version

    async def _visible(
        self, record: ReportRecord, version: ReportVersion
    ) -> tuple[CitationVerdict, ...]:
        # A verdict whose recorded scope no longer matches the report is never released.
        rows = await self.verdicts.for_version(version.id, MAX_VERSION_VERDICTS)
        return tuple(
            row
            for row in rows
            if row.report_id == record.id
            and (row.owner_id, row.team_id) == (record.created_by, record.team_id)
        )

    @staticmethod
    def _can_record(access: AccessContext, record: ReportRecord) -> bool:
        try:
            access.require_create(record.team_id)
        except AppError:
            return False
        return True

    async def list(self, claims: AccessClaims, report_id: UUID, number: int) -> CitationVerdictList:
        access = await self._read_context(claims)
        record, version = await self._version(access, report_id, number)
        rows = await self._visible(record, version)
        return CitationVerdictList(rows, self._can_record(access, record), MAX_VERSION_VERDICTS)

    async def export(
        self, claims: AccessClaims, report_id: UUID, number: int
    ) -> CitationVerdictExport:
        access = await self._read_context(claims)
        record, version = await self._version(access, report_id, number)
        rows = await self._visible(record, version)
        content = encode_verdict_export(version, rows, self.clock.now())
        return CitationVerdictExport(
            f"citation-verdicts-{record.id}-v{version.number}.jsonl", content
        )

    async def record(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
        value: CitationVerdictInput,
        context: RequestContext,
    ) -> CitationVerdict:
        # All work is local. Hold the identity and membership guard through commit.
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        access = await self._read_context(claims)
        record, version = await self._version(access, report_id, number)
        access.require_create(record.team_id)
        try:
            anchor = cited_anchor(version.body, value.judgement_id, value.label, value.relation)
            verdict = CitationVerdict(
                uuid4(),
                record.id,
                version.id,
                version.number,
                anchor,
                value.verdict,
                value.note,
                record.created_by,
                record.team_id,
                access.actor.id,
                self.clock.now(),
            )
        except ValueError as exc:
            raise InvalidRequest(
                "Choose a citation recorded on this saved judgement and a valid verdict."
            ) from exc
        if await self.verdicts.count_for_version(version.id) >= MAX_VERSION_VERDICTS:
            raise InvalidRequest("This report version has reached its citation verdict limit.")
        if await self.verdicts.count_for_anchor(version.id, anchor) >= MAX_CITATION_VERDICTS:
            raise InvalidRequest("This citation has reached its verdict limit.")
        await self.verdicts.add(verdict)
        await self.auditor.record(
            AuditAction.CITATION_VERDICT_RECORDED,
            actor=access.actor.id,
            subject=str(verdict.id),
            ip=context.ip,
            details={
                "report_id": str(record.id),
                "version": version.number,
                "verdict": verdict.verdict.value,
            },
        )
        # Re-check the session after the writes and before they become durable.
        await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.uow.commit()
        return verdict

"""Conditional immutable identity decision writes. Application owns authorisation and quotas."""

import re
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.identity_models import IdentityDecisionRow, IdentityRevisionRow
from ase.adapters.persistence.identity_payloads import (
    decode_identity_revision,
    encode_identity_revision,
)
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.access import Visibility
from ase.domain.identity_review import IdentityDecisionRevision, IdentityDisposition
from ase.domain.identity_roots import IdentityDecisionRoot


def _row(value: IdentityDecisionRevision) -> IdentityRevisionRow:
    payload, digest, size = encode_identity_revision(value)
    return IdentityRevisionRow(
        id=value.id,
        decision_id=value.decision_id,
        number=value.number,
        payload=payload,
        content_sha256=digest,
        byte_size=size,
    )


class SqlIdentityDecisionRepository:
    async def candidate_id(self, version_id: UUID, label: str) -> UUID | None:
        result: UUID | None = await self.session.scalar(
            select(IdentityDecisionRow.id).where(
                IdentityDecisionRow.report_version_id == version_id,
                IdentityDecisionRow.candidate_label == label,
            )
        )
        return result

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_ids(
        self, visibility: Visibility, report_id: UUID, version_id: UUID, limit: int, offset: int
    ) -> tuple[tuple[UUID, ...], int]:
        scope = (
            select(IdentityDecisionRow.id)
            .join(ReportRow, ReportRow.id == IdentityDecisionRow.report_id)
            .where(
                IdentityDecisionRow.report_id == report_id,
                IdentityDecisionRow.report_version_id == version_id,
                visibility_predicate(
                    IdentityDecisionRow.created_by, IdentityDecisionRow.team_id, visibility
                ),
                visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            )
        )
        total = int(
            await self.session.scalar(select(func.count()).select_from(scope.subquery())) or 0
        )
        ids = tuple(
            await self.session.scalars(
                scope.order_by(IdentityDecisionRow.created_at.desc(), IdentityDecisionRow.id)
                .offset(offset)
                .limit(limit)
            )
        )
        return ids, total

    async def get(self, decision_id: UUID) -> IdentityDecisionRoot | None:
        result = (
            await self.session.execute(
                select(IdentityDecisionRow, ReportVersionRow.number)
                .join(
                    ReportVersionRow,
                    and_(
                        ReportVersionRow.id == IdentityDecisionRow.report_version_id,
                        ReportVersionRow.report_id == IdentityDecisionRow.report_id,
                    ),
                )
                .where(IdentityDecisionRow.id == decision_id)
                .execution_options(populate_existing=True)
            )
        ).first()
        if result is None:
            return None
        row, number = result
        return IdentityDecisionRoot(
            row.id,
            row.report_id,
            row.report_version_id,
            number,
            row.created_by,
            row.team_id,
            row.subject,
            row.candidate_label,
            row.evidence_sha256,
            row.latest_revision_id,
            row.created_at,
        )

    def storage_size(self, revision: IdentityDecisionRevision) -> int:
        return encode_identity_revision(revision)[2]

    async def scope_usage(self, owner_id: UUID, team_id: UUID | None) -> tuple[int, int]:
        scope = (
            IdentityDecisionRow.team_id == team_id
            if team_id is not None
            else and_(
                IdentityDecisionRow.team_id.is_(None),
                IdentityDecisionRow.created_by == owner_id,
            )
        )
        count = await self.session.scalar(
            select(func.count()).select_from(IdentityDecisionRow).where(scope)
        )
        size = await self.session.scalar(
            select(func.sum(IdentityRevisionRow.byte_size))
            .join(
                IdentityDecisionRow,
                IdentityDecisionRow.id == IdentityRevisionRow.decision_id,
            )
            .where(scope)
        )
        return int(count or 0), int(size or 0)

    async def revision(
        self, decision_id: UUID, revision_id: UUID
    ) -> IdentityDecisionRevision | None:
        row = await self.session.scalar(
            select(IdentityRevisionRow)
            .where(
                IdentityRevisionRow.decision_id == decision_id,
                IdentityRevisionRow.id == revision_id,
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            return None
        result = decode_identity_revision(row.payload, row.content_sha256, row.byte_size)
        if (result.id, result.decision_id, result.number) != (row.id, row.decision_id, row.number):
            raise ValueError("Identity revision index mismatch")
        return result

    async def create(self, revision: IdentityDecisionRevision, evidence_sha256: str) -> None:
        if (
            revision.number != 1
            or revision.previous_id is not None
            or revision.disposition is IdentityDisposition.WITHDRAWN
            or re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None
        ):
            raise ValueError("Invalid initial identity revision")
        parent = await self.session.scalar(
            select(ReportRow)
            .join(
                ReportVersionRow,
                ReportVersionRow.report_id == ReportRow.id,
            )
            .where(
                ReportRow.id == revision.report_id,
                ReportVersionRow.id == revision.report_version_id,
            )
        )
        if parent is None:
            raise ValueError("Identity review requires its exact parent report version")
        row = _row(revision)
        self.session.add(
            IdentityDecisionRow(
                id=revision.decision_id,
                report_id=revision.report_id,
                report_version_id=revision.report_version_id,
                created_by=revision.authored_by
                if parent.team_id is not None
                else parent.created_by,
                team_id=parent.team_id,
                subject=revision.subject,
                candidate_label=revision.candidate.candidate.evidence_label,
                evidence_sha256=evidence_sha256,
                latest_revision_id=revision.id,
                created_at=revision.created_at,
            )
        )
        await self.session.flush()
        self.session.add(row)
        await self.session.flush()

    async def append(self, revision: IdentityDecisionRevision, base_revision_id: UUID) -> bool:
        if revision.previous_id != base_revision_id or revision.id == base_revision_id:
            raise ValueError("Correction must identify its preceding revision")
        previous = await self.revision(revision.decision_id, base_revision_id)
        if previous is None or revision.created_at < previous.created_at:
            return False
        if revision.subject != previous.subject or revision.candidate != previous.candidate:
            raise ValueError("Identity correction must preserve subject and candidate")
        row = _row(revision)
        previous_exists = exists().where(
            IdentityRevisionRow.id == base_revision_id,
            IdentityRevisionRow.decision_id == IdentityDecisionRow.id,
            IdentityRevisionRow.number == revision.number - 1,
        )
        changed = await self.session.scalar(
            update(IdentityDecisionRow)
            .where(
                IdentityDecisionRow.id == revision.decision_id,
                IdentityDecisionRow.report_id == revision.report_id,
                IdentityDecisionRow.report_version_id == revision.report_version_id,
                IdentityDecisionRow.latest_revision_id == base_revision_id,
                IdentityDecisionRow.subject == revision.subject,
                IdentityDecisionRow.candidate_label == revision.candidate.candidate.evidence_label,
                previous_exists,
            )
            .values(latest_revision_id=revision.id)
            .returning(IdentityDecisionRow.id)
            .execution_options(synchronize_session=False)
        )
        if changed is None:
            return False
        self.session.add(row)
        await self.session.flush()
        return True

    async def delete_for_report(self, report_id: UUID) -> None:
        ids = select(IdentityDecisionRow.id).where(IdentityDecisionRow.report_id == report_id)
        await self.session.execute(
            delete(IdentityRevisionRow).where(IdentityRevisionRow.decision_id.in_(ids))
        )
        await self.session.execute(
            delete(IdentityDecisionRow).where(IdentityDecisionRow.report_id == report_id)
        )

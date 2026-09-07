"""Conditional immutable claim writes. Application owns authorisation and quotas."""

import re
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.claim_models import ClaimRevisionRow, ClaimRow
from ase.adapters.persistence.claim_payloads import decode_revision, encode_revision
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.access import Visibility
from ase.domain.claim_revisions import ClaimReviewState, ClaimRevision
from ase.domain.claim_roots import ClaimRoot


def _row(value: ClaimRevision) -> ClaimRevisionRow:
    payload, digest, size = encode_revision(value)
    return ClaimRevisionRow(
        id=value.id,
        claim_id=value.claim_id,
        number=value.number,
        payload=payload,
        content_sha256=digest,
        byte_size=size,
    )


class SqlClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_ids(
        self, visibility: Visibility, report_id: UUID, version_id: UUID, limit: int, offset: int
    ) -> tuple[tuple[UUID, ...], int]:
        scope = (
            select(ClaimRow.id)
            .join(ReportRow, ReportRow.id == ClaimRow.report_id)
            .where(
                ClaimRow.report_id == report_id,
                ClaimRow.report_version_id == version_id,
                visibility_predicate(ClaimRow.created_by, ClaimRow.team_id, visibility),
                visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            )
        )
        total = int(
            await self.session.scalar(select(func.count()).select_from(scope.subquery())) or 0
        )
        ids = tuple(
            await self.session.scalars(
                scope.order_by(ClaimRow.created_at.desc(), ClaimRow.id).offset(offset).limit(limit)
            )
        )
        return ids, total

    async def get(self, claim_id: UUID) -> ClaimRoot | None:
        result = (
            await self.session.execute(
                select(ClaimRow, ReportVersionRow.number)
                .join(
                    ReportVersionRow,
                    and_(
                        ReportVersionRow.id == ClaimRow.report_version_id,
                        ReportVersionRow.report_id == ClaimRow.report_id,
                    ),
                )
                .where(ClaimRow.id == claim_id)
                .execution_options(populate_existing=True)
            )
        ).first()
        if result is None:
            return None
        row, number = result
        return ClaimRoot(
            row.id,
            row.report_id,
            row.report_version_id,
            number,
            row.created_by,
            row.team_id,
            row.evidence_sha256,
            row.latest_revision_id,
            row.created_at,
        )

    def storage_size(self, revision: ClaimRevision) -> int:
        return encode_revision(revision)[2]

    async def scope_usage(self, owner_id: UUID, team_id: UUID | None) -> tuple[int, int]:
        scope = (
            ClaimRow.team_id == team_id
            if team_id is not None
            else and_(
                ClaimRow.team_id.is_(None),
                ClaimRow.created_by == owner_id,
            )
        )
        count = await self.session.scalar(select(func.count()).select_from(ClaimRow).where(scope))
        size = await self.session.scalar(
            select(func.sum(ClaimRevisionRow.byte_size))
            .join(
                ClaimRow,
                ClaimRow.id == ClaimRevisionRow.claim_id,
            )
            .where(scope)
        )
        return int(count or 0), int(size or 0)

    async def revision(self, claim_id: UUID, revision_id: UUID) -> ClaimRevision | None:
        row = await self.session.scalar(
            select(ClaimRevisionRow)
            .where(
                ClaimRevisionRow.claim_id == claim_id,
                ClaimRevisionRow.id == revision_id,
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            return None
        result = decode_revision(row.payload, row.content_sha256, row.byte_size)
        if (result.id, result.claim_id, result.number) != (row.id, row.claim_id, row.number):
            raise ValueError("Claim revision index mismatch")
        return result

    async def create(self, revision: ClaimRevision, evidence_sha256: str) -> None:
        if (
            revision.number != 1
            or revision.previous_id is not None
            or revision.state is not ClaimReviewState.PROPOSED
            or re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None
        ):
            raise ValueError("Invalid initial claim revision")
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
            raise ValueError("Claim requires its exact parent report version")
        row = _row(revision)
        self.session.add(
            ClaimRow(
                id=revision.claim_id,
                report_id=revision.report_id,
                report_version_id=revision.report_version_id,
                created_by=revision.authored_by
                if parent.team_id is not None
                else parent.created_by,
                team_id=parent.team_id,
                evidence_sha256=evidence_sha256,
                latest_revision_id=revision.id,
                created_at=revision.created_at,
            )
        )
        await self.session.flush()
        self.session.add(row)
        await self.session.flush()

    async def append(self, revision: ClaimRevision, base_revision_id: UUID) -> bool:
        if revision.previous_id != base_revision_id or revision.id == base_revision_id:
            raise ValueError("Correction must identify its preceding revision")
        previous = await self.revision(revision.claim_id, base_revision_id)
        if previous is None or revision.created_at < previous.created_at:
            return False
        row = _row(revision)
        previous_exists = exists().where(
            ClaimRevisionRow.id == base_revision_id,
            ClaimRevisionRow.claim_id == ClaimRow.id,
            ClaimRevisionRow.number == revision.number - 1,
        )
        changed = await self.session.scalar(
            update(ClaimRow)
            .where(
                ClaimRow.id == revision.claim_id,
                ClaimRow.report_id == revision.report_id,
                ClaimRow.report_version_id == revision.report_version_id,
                ClaimRow.latest_revision_id == base_revision_id,
                previous_exists,
            )
            .values(latest_revision_id=revision.id)
            .returning(ClaimRow.id)
            .execution_options(synchronize_session=False)
        )
        if changed is None:
            return False
        self.session.add(row)
        await self.session.flush()
        return True

    async def delete_for_report(self, report_id: UUID) -> None:
        ids = select(ClaimRow.id).where(ClaimRow.report_id == report_id)
        await self.session.execute(
            delete(ClaimRevisionRow).where(ClaimRevisionRow.claim_id.in_(ids))
        )
        await self.session.execute(delete(ClaimRow).where(ClaimRow.report_id == report_id))

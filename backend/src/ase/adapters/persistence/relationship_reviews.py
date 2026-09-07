"""Conditional immutable relationship decision writes. Application owns authorisation and quotas."""

import re
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.relationship_models import (
    RelationshipReviewRow,
    RelationshipRevisionRow,
)
from ase.adapters.persistence.relationship_payloads import (
    decode_relationship_revision,
    encode_relationship_revision,
)
from ase.domain.access import Visibility
from ase.domain.relationship_review import RelationshipDisposition, RelationshipReviewRevision
from ase.domain.relationship_roots import RelationshipReviewRoot


def _row(value: RelationshipReviewRevision) -> RelationshipRevisionRow:
    payload, digest, size = encode_relationship_revision(value)
    return RelationshipRevisionRow(
        id=value.id,
        relationship_id=value.relationship_id,
        number=value.number,
        payload=payload,
        content_sha256=digest,
        byte_size=size,
    )


class SqlRelationshipReviewRepository:
    async def assertion_id(self, version_id: UUID, label: str) -> UUID | None:
        result: UUID | None = await self.session.scalar(
            select(RelationshipReviewRow.id).where(
                RelationshipReviewRow.report_version_id == version_id,
                RelationshipReviewRow.evidence_label == label,
            )
        )
        return result

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_ids(
        self, visibility: Visibility, report_id: UUID, version_id: UUID, limit: int, offset: int
    ) -> tuple[tuple[UUID, ...], int]:
        scope = (
            select(RelationshipReviewRow.id)
            .join(ReportRow, ReportRow.id == RelationshipReviewRow.report_id)
            .where(
                RelationshipReviewRow.report_id == report_id,
                RelationshipReviewRow.report_version_id == version_id,
                visibility_predicate(
                    RelationshipReviewRow.created_by, RelationshipReviewRow.team_id, visibility
                ),
                visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            )
        )
        total = int(
            await self.session.scalar(select(func.count()).select_from(scope.subquery())) or 0
        )
        ids = tuple(
            await self.session.scalars(
                scope.order_by(RelationshipReviewRow.created_at.desc(), RelationshipReviewRow.id)
                .offset(offset)
                .limit(limit)
            )
        )
        return ids, total

    async def get(self, relationship_id: UUID) -> RelationshipReviewRoot | None:
        result = (
            await self.session.execute(
                select(RelationshipReviewRow, ReportVersionRow.number)
                .join(
                    ReportVersionRow,
                    and_(
                        ReportVersionRow.id == RelationshipReviewRow.report_version_id,
                        ReportVersionRow.report_id == RelationshipReviewRow.report_id,
                    ),
                )
                .where(RelationshipReviewRow.id == relationship_id)
                .execution_options(populate_existing=True)
            )
        ).first()
        if result is None:
            return None
        row, number = result
        return RelationshipReviewRoot(
            row.id,
            row.report_id,
            row.report_version_id,
            number,
            row.created_by,
            row.team_id,
            row.evidence_label,
            row.evidence_sha256,
            row.latest_revision_id,
            row.created_at,
        )

    def storage_size(self, revision: RelationshipReviewRevision) -> int:
        return encode_relationship_revision(revision)[2]

    async def scope_usage(self, owner_id: UUID, team_id: UUID | None) -> tuple[int, int]:
        scope = (
            RelationshipReviewRow.team_id == team_id
            if team_id is not None
            else and_(
                RelationshipReviewRow.team_id.is_(None),
                RelationshipReviewRow.created_by == owner_id,
            )
        )
        count = await self.session.scalar(
            select(func.count()).select_from(RelationshipReviewRow).where(scope)
        )
        size = await self.session.scalar(
            select(func.sum(RelationshipRevisionRow.byte_size))
            .join(
                RelationshipReviewRow,
                RelationshipReviewRow.id == RelationshipRevisionRow.relationship_id,
            )
            .where(scope)
        )
        return int(count or 0), int(size or 0)

    async def revision(
        self, relationship_id: UUID, revision_id: UUID
    ) -> RelationshipReviewRevision | None:
        row = await self.session.scalar(
            select(RelationshipRevisionRow)
            .where(
                RelationshipRevisionRow.relationship_id == relationship_id,
                RelationshipRevisionRow.id == revision_id,
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            return None
        result = decode_relationship_revision(row.payload, row.content_sha256, row.byte_size)
        if (result.id, result.relationship_id, result.number) != (
            row.id,
            row.relationship_id,
            row.number,
        ):
            raise ValueError("Relationship revision index mismatch")
        return result

    async def create(self, revision: RelationshipReviewRevision, evidence_sha256: str) -> None:
        if (
            revision.number != 1
            or revision.previous_id is not None
            or revision.disposition is RelationshipDisposition.WITHDRAWN
            or re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None
        ):
            raise ValueError("Invalid initial relationship revision")
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
            raise ValueError("Relationship review requires its exact parent report version")
        row = _row(revision)
        self.session.add(
            RelationshipReviewRow(
                id=revision.relationship_id,
                report_id=revision.report_id,
                report_version_id=revision.report_version_id,
                created_by=revision.authored_by
                if parent.team_id is not None
                else parent.created_by,
                team_id=parent.team_id,
                evidence_label=revision.assertion.evidence_label,
                evidence_sha256=evidence_sha256,
                latest_revision_id=revision.id,
                created_at=revision.created_at,
            )
        )
        await self.session.flush()
        self.session.add(row)
        await self.session.flush()

    async def append(self, revision: RelationshipReviewRevision, base_revision_id: UUID) -> bool:
        if revision.previous_id != base_revision_id or revision.id == base_revision_id:
            raise ValueError("Correction must identify its preceding revision")
        previous = await self.revision(revision.relationship_id, base_revision_id)
        if previous is None or revision.created_at < previous.created_at:
            return False
        if revision.assertion != previous.assertion:
            raise ValueError("Relationship correction must preserve its assertion")
        row = _row(revision)
        previous_exists = exists().where(
            RelationshipRevisionRow.id == base_revision_id,
            RelationshipRevisionRow.relationship_id == RelationshipReviewRow.id,
            RelationshipRevisionRow.number == revision.number - 1,
        )
        changed = await self.session.scalar(
            update(RelationshipReviewRow)
            .where(
                RelationshipReviewRow.id == revision.relationship_id,
                RelationshipReviewRow.report_id == revision.report_id,
                RelationshipReviewRow.report_version_id == revision.report_version_id,
                RelationshipReviewRow.latest_revision_id == base_revision_id,
                RelationshipReviewRow.evidence_label == revision.assertion.evidence_label,
                previous_exists,
            )
            .values(latest_revision_id=revision.id)
            .returning(RelationshipReviewRow.id)
            .execution_options(synchronize_session=False)
        )
        if changed is None:
            return False
        self.session.add(row)
        await self.session.flush()
        return True

    async def delete_for_report(self, report_id: UUID) -> None:
        ids = select(RelationshipReviewRow.id).where(RelationshipReviewRow.report_id == report_id)
        await self.session.execute(
            delete(RelationshipRevisionRow).where(RelationshipRevisionRow.relationship_id.in_(ids))
        )
        await self.session.execute(
            delete(RelationshipReviewRow).where(RelationshipReviewRow.report_id == report_id)
        )

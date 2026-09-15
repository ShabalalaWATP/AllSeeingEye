"""Atomic scoped reviewer histories; frozen snapshots never consult current grades."""

from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.source_review_models import (
    SourceReviewHeadRow,
    SourceReviewRevisionRow,
    SourceReviewSnapshotRow,
)
from ase.domain.source_review_records import (
    SourceReviewSnapshot,
    decode_review_snapshot,
    decode_source_review,
    encode_review_snapshot,
    encode_source_review,
)
from ase.domain.source_reviews import (
    SourceReviewRevision,
    SourceReviewScope,
    validate_source_review_history,
)


def _scope(scope: SourceReviewScope) -> ColumnElement[bool]:
    return (
        SourceReviewHeadRow.team_id == scope.team_id
        if scope.team_id is not None
        else and_(
            SourceReviewHeadRow.team_id.is_(None), SourceReviewHeadRow.owner_id == scope.owner_id
        )
    )


class SqlSourceReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def history(self, scope: SourceReviewScope, key: str) -> tuple[SourceReviewRevision, ...]:
        head = await self.session.scalar(
            select(SourceReviewHeadRow)
            .where(SourceReviewHeadRow.key == key, _scope(scope))
            .execution_options(populate_existing=True)
        )
        if head is None:
            return ()
        rows = await self.session.scalars(
            select(SourceReviewRevisionRow)
            .where(SourceReviewRevisionRow.head_key == key)
            .order_by(SourceReviewRevisionRow.number)
            .limit(101)
        )
        result = []
        for row in rows:
            revision = decode_source_review(row.payload, row.payload_sha256, row.payload_bytes)
            if (
                revision.key != key
                or revision.review.id != str(row.id)
                or revision.number != row.number
                or revision.review.recorded_at != row.created_at
                or revision.scope.owner_id != head.owner_id
                or revision.scope.team_id != head.team_id
                or revision.kind.value != head.kind
            ):
                raise ValueError("Source review history indexes do not match saved content.")
            result.append(revision)
        history = tuple(result)
        validate_source_review_history(history)
        if not history or history[-1].review.id != str(head.latest_id):
            raise ValueError("Source review head does not match its saved revision history.")
        return history

    async def scope_usage(self, scope: SourceReviewScope) -> tuple[int, int]:
        count = await self.session.scalar(
            select(func.count()).select_from(SourceReviewHeadRow).where(_scope(scope))
        )
        size = await self.session.scalar(
            select(func.sum(SourceReviewRevisionRow.payload_bytes))
            .join(SourceReviewHeadRow, SourceReviewHeadRow.key == SourceReviewRevisionRow.head_key)
            .where(_scope(scope))
        )
        return int(count or 0), int(size or 0)

    async def append(self, value: SourceReviewRevision) -> bool:
        history = await self.history(value.scope, value.key)
        if (history[-1].review.id if history else None) != value.review.supersedes:
            return False
        validate_source_review_history((*history, value))
        payload, digest, size = encode_source_review(value)
        try:
            async with self.session.begin_nested():
                if not history:
                    self.session.add(
                        SourceReviewHeadRow(
                            key=value.key,
                            owner_id=value.scope.owner_id,
                            team_id=value.scope.team_id,
                            kind=value.kind.value,
                            latest_id=UUID(value.review.id),
                        )
                    )
                    await self.session.flush()
                else:
                    changed = await self.session.scalar(
                        update(SourceReviewHeadRow)
                        .where(
                            SourceReviewHeadRow.key == value.key,
                            _scope(value.scope),
                            SourceReviewHeadRow.latest_id == UUID(value.review.supersedes),
                        )
                        .values(latest_id=UUID(value.review.id))
                        .returning(SourceReviewHeadRow.key)
                        .execution_options(synchronize_session=False)
                    )
                    if changed is None:
                        return False
                self.session.add(
                    SourceReviewRevisionRow(
                        id=UUID(value.review.id),
                        head_key=value.key,
                        number=value.number,
                        created_at=value.review.recorded_at,
                        payload=payload,
                        payload_sha256=digest,
                        payload_bytes=size,
                    )
                )
                await self.session.flush()
        except IntegrityError:
            return False
        return True

    async def snapshot_count(self, report_version_id: UUID) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(SourceReviewSnapshotRow)
            .where(SourceReviewSnapshotRow.report_version_id == report_version_id)
        )
        return int(count or 0)

    async def add_snapshot(self, value: SourceReviewSnapshot) -> None:
        parent = await self.session.scalar(
            select(ReportRow)
            .join(ReportVersionRow, ReportVersionRow.report_id == ReportRow.id)
            .where(ReportRow.id == value.report_id, ReportVersionRow.id == value.report_version_id)
        )
        if parent is None or (parent.created_by, parent.team_id) != (
            value.scope.owner_id,
            value.scope.team_id,
        ):
            raise ValueError("Source review snapshots require their exact parent and scope.")
        payload, digest, size = encode_review_snapshot(value)
        self.session.add(
            SourceReviewSnapshotRow(
                id=value.id,
                report_id=value.report_id,
                report_version_id=value.report_version_id,
                owner_id=value.scope.owner_id,
                team_id=value.scope.team_id,
                created_at=value.created_at,
                payload=payload,
                payload_sha256=digest,
                payload_bytes=size,
            )
        )
        await self.session.flush()

    async def snapshot(self, snapshot_id: UUID) -> SourceReviewSnapshot | None:
        row = await self.session.get(SourceReviewSnapshotRow, snapshot_id, populate_existing=True)
        if row is None:
            return None
        value = decode_review_snapshot(row.payload, row.payload_sha256, row.payload_bytes)
        if (
            value.id != row.id
            or value.report_id != row.report_id
            or value.report_version_id != row.report_version_id
            or value.created_at != row.created_at
            or value.scope.owner_id != row.owner_id
            or value.scope.team_id != row.team_id
        ):
            raise ValueError("Source review snapshot indexes do not match saved content.")
        return value


async def delete_source_snapshots_for_report(session: AsyncSession, report_id: UUID) -> None:
    """SQLite parity for report-owned snapshots; reusable reviewer policy history remains."""
    await session.execute(
        delete(SourceReviewSnapshotRow).where(SourceReviewSnapshotRow.report_id == report_id)
    )

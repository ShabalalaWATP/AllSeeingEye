"""Session-scoped durable jobs with atomic revision and lease fencing, never commits."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.adapters.persistence.report_job_admission import fair_queued_ids, no_running_sibling
from ase.adapters.persistence.report_job_codec import (
    PayloadCache,
    from_row,
    payload_columns,
    with_summary,
)
from ase.adapters.persistence.report_job_listing import list_job_page
from ase.adapters.persistence.report_job_models import ReportJobRow as Row
from ase.adapters.persistence.report_job_recovery import recover_expired
from ase.adapters.persistence.report_job_usage_models import ReportJobUsageRow
from ase.adapters.persistence.report_job_usage_projection import sync_usage
from ase.domain.access import Visibility
from ase.domain.report_jobs import (
    CheckpointStatus,
    ReportJob,
    job_error,
    job_lease,
    job_stage,
    job_timestamp,
)


def _page(limit: int, offset: int = 0) -> None:
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("Use a bounded report job page.")


class SqlReportJobRepository:
    def __init__(self, session: AsyncSession, cache: PayloadCache | None = None) -> None:
        self.session = session
        self.cache = cache

    async def add(self, job: ReportJob) -> None:
        # Encode again at the write boundary: the frozen dataclass can contain a
        # caller-mutated nested payload, but storage always takes its own snapshot.
        self.session.add(
            Row(
                id=job.id,
                request_key=job.request_key,
                owner_id=job.owner_id,
                team_id=job.team_id,
                title=job.title,
                status=job.status,
                stage=job.stage,
                created_at=job.created_at,
                updated_at=job.updated_at,
                revision=job.revision,
                lease_token=job.lease_token,
                lease_until=job.lease_until,
                report_id=job.report_id,
                version_id=job.version_id,
                error=job.error,
                brief_id=job.brief_id,
                brief_revision=job.brief_revision,
                **payload_columns(job.payload),
            )
        )
        await self.session.flush()
        await sync_usage(self.session, job.id, job.owner_id, job.created_at, job.payload)

    async def get(self, job_id: UUID) -> ReportJob | None:
        row = await self.session.get(Row, job_id, populate_existing=True)
        return from_row(row, self.cache) if row is not None else None

    async def get_by_request(self, owner_id: UUID, request_key: UUID) -> ReportJob | None:
        row = await self.session.scalar(
            select(Row)
            .where(Row.owner_id == owner_id, Row.request_key == request_key)
            .execution_options(populate_existing=True)
        )
        return from_row(row) if row is not None else None

    async def list_visible(
        self, visibility: Visibility, limit: int = 50, offset: int = 0
    ) -> list[ReportJob]:
        _page(limit, offset)
        rows = await self.session.execute(
            select(Row, Row.summary)
            .options(defer(Row.payload))
            .where(visibility_predicate(Row.owner_id, Row.team_id, visibility))
            .order_by(Row.created_at.desc(), Row.id)
            .offset(offset)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [with_summary(row, summary) for row, summary in rows]

    async def list_page(
        self,
        visibility: Visibility,
        *,
        limit: int,
        statuses: Sequence[str] | None = None,
        include_briefings: bool = False,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[ReportJob]:
        return await list_job_page(
            self.session,
            visibility,
            limit=limit,
            statuses=statuses,
            include_briefings=include_briefings,
            after=after,
        )

    async def count_active(self, owner_id: UUID | None = None) -> int:
        query = select(func.count()).select_from(Row).where(Row.status.in_(("queued", "running")))
        if owner_id is not None:
            query = query.where(Row.owner_id == owner_id)
        return int(await self.session.scalar(query) or 0)

    async def queued(self, limit: int = 10) -> list[UUID]:
        _page(limit)
        return list(await self.session.scalars(fair_queued_ids(limit)))

    async def count_open(self, owner_id: UUID | None = None) -> int:
        query = (
            select(func.count())
            .select_from(Row)
            .where(Row.status.not_in(("completed", "needs_review")))
        )
        if owner_id is not None:
            query = query.where(Row.owner_id == owner_id)
        return int(await self.session.scalar(query) or 0)

    async def _update(
        self,
        job_id: UUID,
        expected_revision: int,
        now: datetime,
        predicates: tuple[ColumnElement[bool], ...],
        values: dict[str, Any],
    ) -> ReportJob | None:
        job_timestamp(now)
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("Use a valid report job revision.")
        key = await self.session.scalar(
            update(Row)
            .where(
                Row.id == job_id,
                Row.revision == expected_revision,
                Row.updated_at <= now,
                *predicates,
            )
            .values(**values, updated_at=now, revision=Row.revision + 1)
            .returning(Row.id)
            .execution_options(synchronize_session=False)
        )
        result = await self.get(key) if key is not None else None
        if result is not None and "payload" in values:
            await sync_usage(
                self.session, result.id, result.owner_id, result.created_at, result.payload
            )
        return result

    async def claim(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        lease_token: UUID,
        now: datetime,
        lease_until: datetime,
    ) -> ReportJob | None:
        job_lease(now, lease_until)
        try:
            # The partial unique index closes the concurrent-claim race. The
            # savepoint converts that expected contention into a clean miss.
            async with self.session.begin_nested():
                return await self._update(
                    job_id,
                    expected_revision,
                    now,
                    (Row.status == "queued", Row.lease_token.is_(None), no_running_sibling()),
                    {
                        "status": "running",
                        "lease_token": lease_token,
                        "lease_until": lease_until,
                        "error": None,
                    },
                )
        except IntegrityError:
            return None

    async def checkpoint(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        lease_token: UUID,
        payload: dict[str, Any],
        stage: str,
        now: datetime,
        status: CheckpointStatus = "running",
        error: str | None = None,
        lease_until: datetime | None = None,
    ) -> ReportJob | None:
        if status not in ("running", "paused", "failed"):
            raise ValueError("Use the finalisation operation to complete a report job.")
        job_stage(stage)
        job_error(error)
        values = {**payload_columns(payload), "status": status, "stage": stage, "error": error}
        if status != "running":
            values.update(lease_token=None, lease_until=None)
        elif lease_until is not None:
            job_lease(now, lease_until)
            values["lease_until"] = lease_until
        # A stopped worker may retain its known outcome after time has elapsed,
        # but only while the same token and revision still own the running row.
        # Continued work and publication still require an unexpired lease.
        predicates: tuple[ColumnElement[bool], ...] = (
            Row.status == "running",
            Row.lease_token == lease_token,
        )
        if status == "running":
            predicates += (Row.lease_until > now,)
        return await self._update(
            job_id,
            expected_revision,
            now,
            predicates,
            values,
        )

    async def pause(
        self, job_id: UUID, *, expected_revision: int, now: datetime, error: str | None = None
    ) -> ReportJob | None:
        job_error(error)
        return await self._update(
            job_id,
            expected_revision,
            now,
            (Row.status.in_(("queued", "running")),),
            {"status": "paused", "lease_token": None, "lease_until": None, "error": error},
        )

    async def resume(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        now: datetime,
        payload: dict[str, Any] | None = None,
    ) -> ReportJob | None:
        return await self._update(
            job_id,
            expected_revision,
            now,
            (Row.status.in_(("paused", "failed")),),
            {
                "status": "queued",
                "lease_token": None,
                "lease_until": None,
                "error": None,
                **(payload_columns(payload) if payload is not None else {}),
            },
        )

    async def complete(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        lease_token: UUID,
        payload: dict[str, Any],
        now: datetime,
        needs_review: bool = False,
    ) -> ReportJob | None:
        return await self._update(
            job_id,
            expected_revision,
            now,
            (Row.status == "running", Row.lease_token == lease_token, Row.lease_until > now),
            {
                **payload_columns(payload),
                "status": "needs_review" if needs_review else "completed",
                "stage": "completed",
                "lease_token": None,
                "lease_until": None,
                "error": None,
            },
        )

    async def recover_expired(self, now: datetime, limit: int = 20) -> int:
        job_timestamp(now)
        _page(limit)
        return await recover_expired(self.session, now, limit)

    async def discard(self, job_id: UUID, *, expected_revision: int) -> bool:
        """Remove inactive checkpoints only; final reports and usage remain independent."""
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("Use a valid report job revision.")
        eligible = await self.session.scalar(
            update(Row)
            .where(
                Row.id == job_id,
                Row.revision == expected_revision,
                Row.status.in_(("paused", "failed", "completed", "needs_review")),
            )
            .values(revision=Row.revision + 1)
            .returning(Row.id)
            .execution_options(synchronize_session=False)
        )
        if eligible is None:
            return False
        await self.session.execute(
            delete(ReportJobUsageRow).where(ReportJobUsageRow.job_id == job_id)
        )
        removed = await self.session.scalar(delete(Row).where(Row.id == job_id).returning(Row.id))
        if removed is not None:
            await SqlOriginalPassageRepository(self.session).delete_for_job(job_id)
        return removed is not None

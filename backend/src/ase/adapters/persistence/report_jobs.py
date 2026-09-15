"""Session-scoped durable jobs with atomic revision and lease fencing, never commits."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ColumnElement, cast, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.adapters.persistence.report_job_codec import from_row, payload_columns, with_payload
from ase.adapters.persistence.report_job_models import ReportJobRow as Row
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
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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

    async def get(self, job_id: UUID) -> ReportJob | None:
        row = await self.session.get(Row, job_id, populate_existing=True)
        return from_row(row) if row is not None else None

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
        summary = (
            func.json_extract(Row.payload, "$.summary", type_=JSON)
            if self.session.get_bind().dialect.name == "sqlite"
            else cast(Row.payload, JSON)["summary"]
        )
        rows = await self.session.execute(
            select(Row, summary)
            .options(defer(Row.payload))
            .where(visibility_predicate(Row.owner_id, Row.team_id, visibility))
            .order_by(Row.created_at.desc(), Row.id)
            .offset(offset)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [
            with_payload(row, {"schema_version": 1, "summary": summary or {}})
            for row, summary in rows
        ]

    async def count_active(self, owner_id: UUID | None = None) -> int:
        query = select(func.count()).select_from(Row).where(Row.status.in_(("queued", "running")))
        if owner_id is not None:
            query = query.where(Row.owner_id == owner_id)
        return int(await self.session.scalar(query) or 0)

    async def queued(self, limit: int = 10) -> list[UUID]:
        _page(limit)
        return list(
            await self.session.scalars(
                select(Row.id)
                .where(Row.status == "queued")
                .order_by(Row.created_at, Row.id)
                .limit(limit)
            )
        )

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
        return await self.get(key) if key is not None else None

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
        return await self._update(
            job_id,
            expected_revision,
            now,
            (Row.status == "queued", Row.lease_token.is_(None)),
            {
                "status": "running",
                "lease_token": lease_token,
                "lease_until": lease_until,
                "error": None,
            },
        )

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
        return await self._update(
            job_id,
            expected_revision,
            now,
            (Row.status == "running", Row.lease_token == lease_token, Row.lease_until > now),
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
        rows = await self.session.execute(
            select(Row.id, Row.revision)
            .where(Row.status == "running", Row.lease_until <= now)
            .order_by(Row.lease_until, Row.id)
            .limit(limit)
        )
        count = 0
        for job_id, revision in rows:
            value = await self._update(
                job_id,
                revision,
                now,
                (Row.status == "running", Row.lease_until <= now),
                {
                    "status": "paused",
                    "lease_token": None,
                    "lease_until": None,
                    "error": "interrupted_uncertain",
                },
            )
            count += value is not None
        return count

    async def discard(self, job_id: UUID, *, expected_revision: int) -> bool:
        """Remove inactive checkpoints only; final reports and usage remain independent."""
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("Use a valid report job revision.")
        removed = await self.session.scalar(
            delete(Row)
            .where(
                Row.id == job_id,
                Row.revision == expected_revision,
                Row.status.in_(("paused", "failed", "completed", "needs_review")),
            )
            .returning(Row.id)
            .execution_options(synchronize_session=False)
        )
        if removed is not None:
            await SqlOriginalPassageRepository(self.session).delete_for_job(job_id)
        return removed is not None

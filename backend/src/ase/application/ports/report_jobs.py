"""Transactional storage for resumable report checkpoints, without provider calls."""

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.report_jobs import CheckpointStatus, ReportJob


class ReportJobRepository(Protocol):
    async def add(self, job: ReportJob) -> None: ...
    async def get(self, job_id: UUID) -> ReportJob | None: ...
    async def get_by_request(self, owner_id: UUID, request_key: UUID) -> ReportJob | None: ...
    async def list_visible(
        self, visibility: Visibility, limit: int = 50, offset: int = 0
    ) -> list[ReportJob]: ...
    async def count_active(self, owner_id: UUID | None = None) -> int: ...
    async def count_open(self, owner_id: UUID | None = None) -> int: ...
    async def queued(self, limit: int = 10) -> list[UUID]: ...
    async def claim(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        lease_token: UUID,
        now: datetime,
        lease_until: datetime,
    ) -> ReportJob | None: ...
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
    ) -> ReportJob | None: ...
    async def pause(
        self, job_id: UUID, *, expected_revision: int, now: datetime, error: str | None = None
    ) -> ReportJob | None: ...
    async def resume(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        now: datetime,
        payload: dict[str, Any] | None = None,
    ) -> ReportJob | None: ...
    async def complete(
        self,
        job_id: UUID,
        *,
        expected_revision: int,
        lease_token: UUID,
        payload: dict[str, Any],
        now: datetime,
        needs_review: bool = False,
    ) -> ReportJob | None: ...
    async def recover_expired(self, now: datetime, limit: int = 20) -> int: ...
    async def discard(self, job_id: UUID, *, expected_revision: int) -> bool: ...

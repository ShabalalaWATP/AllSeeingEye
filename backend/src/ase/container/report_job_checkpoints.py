"""Fresh-transaction, lease-fenced collection and section checkpoints for report workers."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.ports.section_checkpoints import SectionCheckpoint, SectionCheckpoints
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.report_jobs.views import refresh_summary
from ase.application.reports.production_checkpoint import (
    ProductionSnapshot,
    collection_from_dict,
    collection_to_dict,
)
from ase.container.report_job_usage import settled_usage
from ase.domain.report_jobs import ReportJob, job_error

if TYPE_CHECKING:
    from ase.container import Container

LEASE_SECONDS = 45


class ReportJobCheckpoints:
    def __init__(self, container: Container, job_id: UUID, lease_token: UUID) -> None:
        self.container, self.job_id, self.lease_token = container, job_id, lease_token
        self._lock = asyncio.Lock()
        self._sections = _Sections(self)

    def _leased(self, job: ReportJob | None) -> ReportJob:
        if (
            job is None
            or job.status != "running"
            or job.lease_token != self.lease_token
            or job.lease_until is None
            or job.lease_until <= self.container.clock.now()
        ):
            raise JobInterrupted()
        return job

    async def _authorised(self, session: AsyncSession, *, reset: bool = True) -> ReportJob:
        repository = SqlReportJobRepository(session)
        initial = self._leased(await repository.get(self.job_id))
        if reset:
            await session.rollback()
        await self.container.access_policy(session).background(
            initial.owner_id, initial.team_id, for_update=True
        )
        current = self._leased(await repository.get(self.job_id))
        await self.container.report_job_gate(session, current)
        return self._leased(current)

    async def _read(self) -> dict[str, Any]:
        async with (
            self._lock,
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            try:
                return deepcopy((await self._authorised(session)).payload)
            finally:
                await session.rollback()

    async def check(self) -> None:
        await self._read()

    async def _account(
        self, session: AsyncSession, job: ReportJob, payload: dict[str, Any]
    ) -> None:
        entries = settled_usage(job.payload, payload, job.owner_id, self.container.clock.now())
        usage = self.container.repositories(session).llm_usage
        for entry in entries:
            await usage.add(entry)

    async def mutate(self, callback: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        async with (
            self._lock,
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            try:
                job = await self._authorised(session)
                payload = deepcopy(job.payload)
                callback(payload)
                refresh_summary(payload)
                await self.container.report_job_gate(session, replace(job, payload=payload))
                self._leased(job)
                await self._account(session, job, payload)
                now = self.container.clock.now()
                self._leased(job)
                updated = await SqlReportJobRepository(session).checkpoint(
                    self.job_id,
                    expected_revision=job.revision,
                    lease_token=self.lease_token,
                    payload=payload,
                    stage=payload.get("stage", job.stage),
                    now=now,
                    lease_until=now + timedelta(seconds=LEASE_SECONDS),
                )
                if updated is None:
                    raise JobInterrupted()
                await session.commit()
                return updated.payload
            except BaseException:
                await session.rollback()
                raise

    async def load_collection(self) -> ProductionSnapshot | None:
        payload = await self._read()
        value = payload.get("collection")
        return collection_from_dict(value) if value is not None else None

    async def save_collection(self, snapshot: ProductionSnapshot) -> None:
        value = collection_to_dict(snapshot)

        def save(payload: dict[str, Any]) -> None:
            if payload.get("collection") is not None and payload["collection"] != value:
                raise JobInterrupted()
            payload["collection"] = value
            payload["stage"] = "drafting"

        await self.mutate(save)

    @property
    def section_checkpoints(self) -> SectionCheckpoints:
        return self._sections

    async def finish(
        self, session: AsyncSession, payload: dict[str, Any], needs_review: bool = False
    ) -> ReportJob:
        """Caller holds source guard and owns the final report transaction/rollback.

        Do not acquire the local lock here: a heartbeat may already hold it while
        waiting for the caller's source guard. The database lease still fences it.
        """
        job = await self._authorised(session, reset=False)
        payload = deepcopy(payload)
        payload["stage"] = "completed"
        refresh_summary(payload)
        await self.container.report_job_gate(session, replace(job, payload=payload))
        self._leased(job)
        await self._account(session, job, payload)
        self._leased(job)
        final = await SqlReportJobRepository(session).complete(
            self.job_id,
            expected_revision=job.revision,
            lease_token=self.lease_token,
            payload=payload,
            now=self.container.clock.now(),
            needs_review=needs_review,
        )
        if final is None:
            raise JobInterrupted()
        return final


class _Sections:
    def __init__(self, parent: ReportJobCheckpoints) -> None:
        self.parent = parent

    @staticmethod
    def _key(packet_digest: str, section_id: str) -> str:
        if (
            not re.fullmatch(r"[0-9a-f]{64}", packet_digest)
            or not 1 <= len(section_id.strip()) <= 120
            or len(section_id) > 120
            or any(ord(char) < 32 for char in section_id)
        ):
            raise JobInterrupted()
        return f"{packet_digest}:{section_id}"

    async def load(self, packet_digest: str, section_id: str) -> SectionCheckpoint | None:
        key = self._key(packet_digest, section_id)
        payload = await self.parent._read()
        sections = payload.get("sections", {})
        if type(sections) is not dict:
            raise JobInterrupted()
        value = sections.get(key)
        if value is None:
            return None
        if (
            type(value) is not dict
            or value.get("packet_digest") != packet_digest
            or value.get("section_id") != section_id
            or value.get("status") not in {"running", "completed", "split", "incomplete"}
        ):
            raise JobInterrupted()
        return SectionCheckpoint(value["status"], value.get("payload"), value.get("reason"))

    async def save(
        self, packet_digest: str, section_id: str, checkpoint: SectionCheckpoint
    ) -> None:
        key = self._key(packet_digest, section_id)
        if checkpoint.status not in {"running", "completed", "split", "incomplete"} or (
            checkpoint.payload is not None and type(checkpoint.payload) is not dict
        ):
            raise JobInterrupted()
        job_error(checkpoint.reason)
        value = {
            "packet_digest": packet_digest,
            "section_id": section_id,
            "status": checkpoint.status,
            "payload": deepcopy(checkpoint.payload),
            "reason": checkpoint.reason,
        }

        def save(payload: dict[str, Any]) -> None:
            sections = payload.setdefault("sections", {})
            if type(sections) is not dict:
                raise JobInterrupted()
            previous = sections.get(key)
            if previous is not None and type(previous) is not dict:
                raise JobInterrupted()
            if previous and previous.get("status") == "completed" and previous != value:
                raise JobInterrupted()
            sections[key] = value
            payload["current_packet"] = packet_digest
            payload["stage"] = (
                "summarising"
                if (checkpoint.payload or {}).get("kind") == "synthesis"
                else "drafting"
            )

        await self.parent.mutate(save)

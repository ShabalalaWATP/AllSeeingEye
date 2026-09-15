"""Lease-fenced storage for selected excerpts, independent of a running HTTP request."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.research.original_passages import OriginalDocumentVersion
from ase.application.research.original_staging import StagedOriginalPassage

if TYPE_CHECKING:
    from ase.container import Container
    from ase.container.report_job_checkpoints import ReportJobCheckpoints


class CheckedOriginalStaging:
    def __init__(self, container: Container, checkpoints: ReportJobCheckpoints) -> None:
        self.container, self.checkpoints = container, checkpoints

    async def _policy_allows(self, document: OriginalDocumentVersion) -> bool:
        policies = getattr(self.container, "original_source_policies", {})
        policy = policies.get(document.source_id)
        return bool(
            policy is not None
            and policy.policy_id == document.acquisition_policy_id
            and policy.permits(document.canonical_url, self.container.clock.now())
            and await self.container.source_admission.enabled(document.source_id)
        )

    async def staged(
        self, job_id: UUID, event_id: str, now: datetime
    ) -> StagedOriginalPassage | None:
        async with (
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            job = await self.checkpoints._authorised(session)
            if job.id != job_id:
                raise JobInterrupted()
            found = await SqlOriginalPassageRepository(session).staged(job_id, event_id, now)
            if found is not None and (
                found.document.owner_id != job.owner_id
                or found.document.team_id != job.team_id
                or not await self._policy_allows(found.document)
            ):
                found = None
            await session.rollback()
            return found

    async def stage(
        self,
        *,
        job_id: UUID,
        event_id: str,
        evidence_label: str,
        document: OriginalDocumentVersion,
    ) -> StagedOriginalPassage:
        async with (
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            try:
                job = await self.checkpoints._authorised(session)
                if (
                    job.id != job_id
                    or document.owner_id != job.owner_id
                    or document.team_id != job.team_id
                    or not await self._policy_allows(document)
                ):
                    raise JobInterrupted()
                repository = SqlOriginalPassageRepository(session)
                await repository.expire(self.container.clock.now())
                staged = await repository.stage(
                    job_id=job_id,
                    event_id=event_id,
                    evidence_label=evidence_label,
                    document=document,
                )
                await session.commit()
                return staged
            except BaseException:
                await session.rollback()
                raise

"""Link staged excerpts only to the exact authorised frozen report version."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.application.report_jobs.budget import JobInterrupted

if TYPE_CHECKING:
    from ase.container import Container
    from ase.domain.report_jobs import ReportJob
    from ase.domain.report_records import ReportVersion


async def link_original_followup(
    session: AsyncSession, container: "Container", stored: "ReportJob", version: "ReportVersion"
) -> None:
    receipt = version.research
    if receipt is None or not receipt.original_followup:
        return
    repository = SqlOriginalPassageRepository(session)
    evidence = {item.label: item for item in version.evidence}
    now = container.clock.now()
    for row in receipt.original_followup:
        if row.status != "acquired":
            continue
        if row.passage_ref is None:
            raise JobInterrupted()
        item = evidence.get(row.evidence_label)
        staged = await repository.staged(stored.id, row.event_id, now)
        policy = getattr(container, "original_source_policies", {}).get(row.source_id)
        if (
            item is None
            or item.event_id != row.event_id
            or item.source_id != row.source_id
            or staged is None
            or staged.id != row.passage_ref
            or staged.document.id != row.document_version_id
            or staged.document.passages[0].id != row.passage_id
            or staged.document.owner_id != stored.owner_id
            or staged.document.team_id != stored.team_id
            or policy is None
            or policy.policy_id != staged.document.acquisition_policy_id
            or not policy.permits(staged.document.canonical_url, now)
            or not await container.source_admission.enabled(row.source_id)
            or not await repository.link(
                job_id=stored.id,
                ref=staged.id,
                version_id=version.id,
                owner_id=stored.owner_id,
                team_id=stored.team_id,
                event_id=row.event_id,
                evidence_label=row.evidence_label,
                now=now,
            )
        ):
            raise JobInterrupted()

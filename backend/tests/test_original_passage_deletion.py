"""SQLite deletion removes selected excerpt JSON without relying on foreign keys."""

from sqlalchemy import select

from ase.adapters.persistence.original_passage_models import OriginalPassageRow
from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.reports import SqlReportRepository
from original_acquisition_support import NOW, Harness
from report_documents_helpers import document_records
from report_job_helpers import job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401 - pytest fixture


async def test_report_deletion_removes_linked_excerpt_immediately(job_storage):
    _, factory = job_storage
    document = (await Harness().acquire()).document
    assert document is not None
    record, version = document_records(owner=document.owner_id)
    stored_job = await saved(
        factory,
        job(owner_id=document.owner_id, report_id=record.id, version_id=version.id),
    )
    async with factory() as session:
        reports = SqlReportRepository(session)
        passages = SqlOriginalPassageRepository(session)
        await reports.add(record, version)
        staged = await passages.stage(
            job_id=stored_job.id,
            event_id="admitted-event",
            evidence_label="E1",
            document=document,
        )
        assert await passages.link(
            job_id=stored_job.id,
            ref=staged.id,
            version_id=version.id,
            owner_id=document.owner_id,
            team_id=None,
            event_id="admitted-event",
            evidence_label="E1",
            now=NOW,
        )
        await session.commit()
    async with factory() as session:
        await SqlReportRepository(session).delete(record.id)
        await session.commit()
    async with factory() as session:
        assert (
            await session.scalar(
                select(OriginalPassageRow.id).where(OriginalPassageRow.id == staged.id)
            )
            is None
        )


async def test_job_discard_removes_unlinked_staged_excerpt_immediately(job_storage):
    _, factory = job_storage
    document = (await Harness().acquire()).document
    assert document is not None
    stored_job = await saved(factory, job(owner_id=document.owner_id, status="paused"))
    async with factory() as session:
        staged = await SqlOriginalPassageRepository(session).stage(
            job_id=stored_job.id,
            event_id="admitted-event",
            evidence_label="E1",
            document=document,
        )
        await session.commit()
    async with factory() as session:
        assert await SqlReportJobRepository(session).discard(
            stored_job.id, expected_revision=stored_job.revision
        )
        await session.commit()
    async with factory() as session:
        assert (
            await session.scalar(
                select(OriginalPassageRow.id).where(OriginalPassageRow.id == staged.id)
            )
            is None
        )

"""Only the exact selected excerpt survives staging, and it expires physically."""

from datetime import timedelta

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.original_passage_models import OriginalPassageRow
from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from original_acquisition_support import NOW, Harness
from report_job_helpers import job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401 - pytest fixture


async def test_selected_passage_is_hash_checked_unlinked_and_expired(job_storage):
    _, factory = job_storage
    harness = Harness()
    document = (await harness.acquire()).document
    assert document is not None
    stored_job = await saved(factory, job(owner_id=document.owner_id))
    async with factory() as session:
        repository = SqlOriginalPassageRepository(session)
        staged = await repository.stage(
            job_id=stored_job.id,
            event_id="admitted-event",
            evidence_label="E1",
            document=document,
        )
        await session.commit()
    async with factory() as session:
        repository = SqlOriginalPassageRepository(session)
        found = await repository.staged(stored_job.id, "admitted-event", NOW)
        assert found == staged
        assert len(found.document.passages) == 1
        assert found.document.passages[0].text == "Exact original passage."
        assert await repository.linked(staged.id, stored_job.version_id, NOW) is None
        row = await session.scalar(
            select(OriginalPassageRow).where(OriginalPassageRow.id == staged.id)
        )
        assert "Generated discovery summary" not in str(row.snapshot)
        assert await repository.staged(stored_job.id, "admitted-event", staged.expires_at) is None
        await repository.expire(staged.expires_at)
        await session.commit()
    async with factory() as session:
        assert (
            await SqlOriginalPassageRepository(session).staged(stored_job.id, "admitted-event", NOW)
            is None
        )


async def test_mutated_excerpt_fails_closed_on_read(job_storage):
    _, factory = job_storage
    harness = Harness()
    document = (await harness.acquire()).document
    assert document is not None
    stored_job = await saved(factory, job(owner_id=document.owner_id))
    async with factory() as session:
        repository = SqlOriginalPassageRepository(session)
        staged = await repository.stage(
            job_id=stored_job.id,
            event_id="admitted-event",
            evidence_label="E1",
            document=document,
        )
        await session.commit()
    async with factory() as session:
        row = await session.scalar(
            select(OriginalPassageRow).where(OriginalPassageRow.id == staged.id)
        )
        changed = dict(row.snapshot)
        document_payload = dict(changed["document"])
        passages = [dict(passage) for passage in document_payload["passages"]]
        passages[0]["text"] = "Tampered"
        document_payload["passages"] = passages
        changed["document"] = document_payload
        await session.execute(
            update(OriginalPassageRow)
            .where(OriginalPassageRow.id == staged.id)
            .values(snapshot=changed)
        )
        await session.commit()
    async with factory() as session:
        with pytest.raises(ValueError, match="integrity"):
            await SqlOriginalPassageRepository(session).staged(
                stored_job.id, "admitted-event", NOW + timedelta(seconds=1)
            )

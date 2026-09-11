"""Isolated file-backed storage for lease races and restart checkpoints."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.domain.report_jobs import ReportJob

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def job(**changes):
    values = {
        "id": uuid4(),
        "request_key": uuid4(),
        "owner_id": uuid4(),
        "team_id": None,
        "title": "Scoped report",
        "status": "queued",
        "stage": "queued",
        "created_at": NOW,
        "updated_at": NOW,
        "payload": {"schema_version": 1, "summary": {"completed_sections": 0}},
        "report_id": uuid4(),
        "version_id": uuid4(),
    }
    return ReportJob(**(values | changes))


@pytest.fixture(name="job_storage")
async def job_storage(tmp_path):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)
    yield engine, factory
    await engine.dispose()


async def saved(factory, value):
    async with factory() as session:
        await SqlReportJobRepository(session).add(value)
        await session.commit()
    return value

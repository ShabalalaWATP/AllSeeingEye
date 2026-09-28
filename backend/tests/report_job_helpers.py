"""Isolated file-backed storage for lease races and restart checkpoints."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.domain.report_jobs import ReportJob
from pytest_support import create_schema, disposable_database, skip_sqlite_fsync

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
    url = f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}"
    engine = create_engine(url)
    skip_sqlite_fsync(engine)
    await create_schema(engine, fresh=disposable_database(url))
    factory = create_session_factory(engine)
    yield engine, factory
    await engine.dispose()


async def saved(factory, value):
    async with factory() as session:
        await SqlReportJobRepository(session).add(value)
        await session.commit()
    return value

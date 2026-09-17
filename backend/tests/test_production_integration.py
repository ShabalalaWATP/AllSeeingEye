"""Report production keeps every citation and writes usage only after outbound work."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.llm import SqlLlmUsageRepository
from ase.adapters.persistence.models import LlmUsageRow, ReportRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.persistence.session import create_session_factory
from ase.application.reports.production import Producer
from ase.container import Container
from ase.domain.llm import LlmUsage
from ase.domain.reports import ReportStatus
from ase.domain.users import User
from feeds_helpers import NOW
from production_integration_helpers import (
    BarrierResolver,
    RecordingUsage,
    StageGateway,
    production_job,
    production_record,
)
from report_helpers import filled_store


async def test_producer_resolves_advocacy_only_citations_after_model_calls_without_usage_writes(
    container: Container,
    user: User,
) -> None:
    usage = RecordingUsage()

    def no_writes() -> None:
        assert usage.rows == []

    gateway = StageGateway(no_writes)
    resolver = BarrierResolver(before_call=no_writes)
    job = production_job(user, container.cipher)

    async def profile_for(role):
        return job.profile

    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=gateway,
        usage=usage,
        url_resolver=resolver,
    )
    version = await producer.produce(job, profile_for)
    assert gateway.calls == [
        "direction",
        "report",
        "advocacy",
        "report_analysis",
        "entailment",
    ]
    assert version.body.cited_labels() == {"E1"}
    assert version.advocacy is not None and version.advocacy.evidence == ("E2",)
    assert len(resolver.calls) == 2
    assert version.evidence[0].url.endswith("/resolved")
    assert version.evidence[1].url.endswith("/resolved")
    assert not version.evidence[2].url.endswith("/resolved")
    assert [row.purpose for row in usage.rows] == [
        "report:ask:direction",
        "report:ask",
        "report:ask:advocacy",
        "report:ask:analysis",
        "report:ask:entailment",
    ]
    assert all(
        row.ok and row.prompt_tokens == 5 and row.completion_tokens == 3 for row in usage.rows
    )
    # Five calls now: direction, the report, advocacy, the analysis pass and the review.
    assert version.prompt_tokens == 25 and version.completion_tokens == 15


@pytest.mark.parametrize("fail_stage", ["direction", "report", "advocacy"])
async def test_deferred_usage_preserves_failed_call_outcomes(
    container: Container,
    user: User,
    fail_stage: str,
) -> None:
    usage = RecordingUsage()

    def no_writes() -> None:
        assert usage.rows == []

    job = production_job(user, container.cipher)

    async def profile_for(role):
        return job.profile

    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=StageGateway(no_writes, fail_stage),
        usage=usage,
        url_resolver=BarrierResolver(before_call=no_writes),
    )
    version = await producer.produce(job, profile_for)
    failed = [row for row in usage.rows if not row.ok]
    assert len(failed) == 1 and failed[0].error is not None
    expected = "report:ask" if fail_stage == "report" else f"report:ask:{fail_stage}"
    assert failed[0].purpose == expected
    assert (version.status is ReportStatus.FAILED) == (fail_stage == "report")


@pytest.mark.parametrize("commit", [True, False])
async def test_file_sqlite_writer_progresses_during_resolution_and_report_usage_are_atomic(
    container: Container,
    user: User,
    tmp_path: Path,
    commit: bool,
) -> None:
    # Separate connections and a real file expose writer contention hidden by the
    # normal in-memory single-connection fixtures. A short busy timeout fails promptly.
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'production.db').as_posix()}",
        connect_args={"timeout": 0.1},
    )
    sessions = create_session_factory(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    job = production_job(user, container.cipher)
    resolver = BarrierResolver(wait=True)

    async def profile_for(role):
        return job.profile

    try:
        async with sessions() as session:
            producer = Producer(
                store=filled_store(),
                source_profiles={},
                cipher=container.cipher,
                gateway=StageGateway(),
                usage=SqlLlmUsageRepository(session),
                url_resolver=resolver,
            )
            task = asyncio.create_task(producer.produce(job, profile_for))
            try:
                await asyncio.wait_for(resolver.entered.wait(), timeout=3)
                async with sessions() as writer:
                    await SqlLlmUsageRepository(writer).add(
                        LlmUsage(NOW, job.profile.id, user.id, "unrelated-writer", True, 0)
                    )
                    await writer.commit()
            finally:
                resolver.release.set()
                version = await task
            await SqlReportRepository(session).add(production_record(job, version), version)
            if commit:
                await session.commit()
            else:
                await session.rollback()
        async with sessions() as observer:
            assert await observer.scalar(select(func.count()).select_from(ReportRow)) == int(commit)
            rows = list(await observer.scalars(select(LlmUsageRow)))
            # Direction, the report, advocacy and the entailment pass, plus the writer.
            # Five model calls plus the post-draft review when the writer commits.
            assert len(rows) == (6 if commit else 1)
            assert sum(row.purpose == "unrelated-writer" for row in rows) == 1
    finally:
        await engine.dispose()

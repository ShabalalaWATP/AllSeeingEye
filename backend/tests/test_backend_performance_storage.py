"""Query budgets and retention bounds, without timing assertions or live services."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import event, select

from annotation_monitor_helpers import seeded
from ase.adapters.persistence.annotation_monitors import SqlAnnotationMonitorRepository
from ase.adapters.persistence.baselines import SqlBaselineRepository, SqlBaselineSink
from ase.adapters.persistence.models import ActivitySampleRow
from ase.adapters.persistence.monthly_report_usage import monthly_usage
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.access import Visibility
from ase.domain.subscription_monthly_budget import MonthlyUsage
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401


async def test_sampler_prunes_every_kind_and_existing_backlog_in_bounded_statements(job_storage):
    engine, factory = job_storage
    async with factory() as session:
        for kind in ("military_aircraft", "future_indicator"):
            for age in (10, 29, 31, 400):
                session.add(
                    ActivitySampleRow(
                        kind=kind, key=str(age), hour=NOW - timedelta(days=age), value=age
                    )
                )
        session.add_all(
            [
                ActivitySampleRow(
                    kind="retired", key=str(i), hour=NOW - timedelta(days=400), value=1
                )
                for i in range(1100)
            ]
        )
        await session.commit()
        means = await SqlBaselineRepository(session).means(
            "military_aircraft", NOW - timedelta(days=30)
        )
    statements = []

    def capture(_c, _cu, sql, _p, _cx, _m):
        statements.append(sql)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        await SqlBaselineSink(factory).record_many(NOW, [])
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    deletes = [sql for sql in statements if sql.startswith("DELETE")]
    assert len(deletes) == 2 and all("LIMIT" in sql for sql in deletes)
    async with factory() as session:
        rows = list(await session.scalars(select(ActivitySampleRow)))
        assert len(rows) == 4
        assert all(row.hour >= NOW - timedelta(days=30) for row in rows)
        assert (
            await SqlBaselineRepository(session).means(
                "military_aircraft", NOW - timedelta(days=30)
            )
            == means
        )


async def test_monitor_page_uses_three_queries_for_twenty_rows(client, container, user):
    _, _, _, _, monitor = await seeded(client, container, user)
    async with container.session_factory() as session:
        repository = SqlAnnotationMonitorRepository(session)
        payload = await repository.checkpoint(monitor.id)
        for index in range(19):
            await repository.create(replace(monitor, id=uuid4(), name=f"Watch {index}"), payload)
        await session.commit()
    statements = []

    def capture(_c, _cu, sql, _p, _cx, _m):
        statements.append(sql)

    event.listen(container.engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with container.session_factory() as session:
            rows, total = await SqlAnnotationMonitorRepository(session).page(
                Visibility(monitor.created_by, False, ()),
                None,
                None,
                50,
                0,
            )
    finally:
        event.remove(container.engine.sync_engine, "before_cursor_execute", capture)
    assert total == len(rows) == 20 and len(statements) == 3
    assert all(row.watches == monitor.watches for row in rows)
    assert [row.id for row in rows] == sorted(row.id for row in rows)


async def test_recovery_is_two_queries_independent_of_page_size(job_storage):
    engine, factory = job_storage
    for _ in range(20):
        await saved(
            factory,
            job(status="running", lease_token=uuid4(), lease_until=NOW + timedelta(seconds=1)),
        )
    statements = []

    def capture(_c, _cu, sql, _p, _cx, _m):
        statements.append(sql)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with factory() as session:
            assert (
                await SqlReportJobRepository(session).recover_expired(NOW + timedelta(seconds=2))
                == 20
            )
            await session.commit()
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    assert len(statements) == 2


async def test_monthly_usage_counts_reservations_without_reading_job_payloads(job_storage):
    engine, factory = job_storage
    owner = uuid4()
    for _ in range(50):
        await saved(
            factory,
            job(
                owner_id=owner,
                payload={
                    "schema_version": 1,
                    "padding": "x" * 150_000,
                    "calls": [
                        {
                            "status": "uncertain",
                            "reserved_output": 100,
                            "dispatched_at": NOW.isoformat(),
                        }
                    ],
                },
            ),
        )
    statements = []

    def capture(_c, _cu, sql, _p, _cx, _m):
        statements.append(sql)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with factory() as session:
            owner_usage, subscription_usage = await monthly_usage(session, owner, None, NOW)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    assert owner_usage == MonthlyUsage(50, 5000) and subscription_usage == MonthlyUsage()
    assert len(statements) == 2 and all("payload" not in sql for sql in statements)

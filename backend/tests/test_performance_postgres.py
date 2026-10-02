"""Explicit disposable PostgreSQL plan and pool probes. Run serially with -s.

ASE_TEST_DATABASE_URL must name a private disposable PostgreSQL database. The
ordinary app fixture recreates that schema. ASE_PERFORMANCE_LOAD=1 enables the
controlled 32-stream freshness burst alongside six representative worker reads.
"""

# ruff: noqa: T201
# Measurements are an explicit probe deliverable, emitted under pytest -s.

import asyncio
import json
import os
import time
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, insert, select, text, update

from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.report_job_lease import renew_lease
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_job_usage_models import ReportJobUsageRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.report_search import ReportEmbeddingRow, SqlReportEmbeddingRepository
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionAttemptRow,
    SubscriptionEditionRow,
)
from ase.adapters.persistence.subscription_retry_attempts import (
    due_retry_ids,
    reconcile_stopped_attempts,
)
from ase.api.routers.stream import _stream_access
from ase.api.stream_session import LiveStream
from ase.application.ports.feeds import BusMessage
from ase.application.report_jobs.budget import MAX_COUNTER
from ase.domain.access import Visibility
from helpers import USER_EMAIL, USER_PASSWORD, create_user, login_token
from report_job_helpers import job, saved
from test_subscription_retry_worker import _queued

pytestmark = pytest.mark.skipif(
    not os.environ.get("ASE_TEST_DATABASE_URL", "").startswith("postgresql+"),
    reason="Explicit disposable PostgreSQL URL required",
)


def nodes(plan):
    yield plan
    for child in plan.get("Plans", ()):
        yield from nodes(child)


async def test_poll_query_plans_at_retained_history_scale(container, user):
    _, edition, stored = await _queued(container, user)
    now = container.clock.now()
    async with container.session_factory() as session:
        await session.execute(
            update(SubscriptionEditionRow)
            .where(SubscriptionEditionRow.id == edition.id)
            .values(workflow="retry_wait")
        )
        await session.execute(
            insert(SubscriptionAttemptRow),
            [
                {
                    "id": uuid4(),
                    "edition_id": edition.id,
                    "job_id": stored.id,
                    "number": i + 1,
                    "stage": "drafting",
                    "started_at": now - timedelta(seconds=10001 - i),
                    "ended_at": None if i < 5 else now,
                    "outcome": "known_transient_failure",
                    "next_retry_at": now,
                    "reserved_requests": 0,
                    "actual_requests": 0,
                    "reserved_output_tokens": 0,
                    "actual_output_tokens": 0,
                }
                for i in range(10000)
            ],
        )
        original = (
            (
                await session.execute(
                    select(ReportJobRow.__table__).where(ReportJobRow.id == stored.id)
                )
            )
            .mappings()
            .one()
        )
        await session.execute(
            insert(ReportJobRow),
            [
                dict(
                    original,
                    id=uuid4(),
                    request_key=uuid4(),
                    report_id=uuid4(),
                    version_id=uuid4(),
                    created_at=now - timedelta(seconds=i + 1),
                )
                for i in range(999)
            ],
        )
        reports = [
            {
                "id": uuid4(),
                "template": "intsum",
                "title": f"Fixture {i}",
                "scope": {},
                "period_from": now - timedelta(days=1),
                "period_to": now,
                "data_cutoff": now,
                "status": "ready",
                "created_by": user.id,
                "created_at": now - timedelta(seconds=i),
                "latest_version": 1,
            }
            for i in range(1000)
        ]
        await session.execute(insert(ReportRow), reports)
        await session.execute(
            insert(ReportEmbeddingRow),
            [
                {
                    "report_id": row["id"],
                    "version": 1,
                    "fingerprint": "f" * 64,
                    "vector": [1.0] + [0.0] * 127,
                    "vector_valid": True,
                }
                for row in reports
            ],
        )
        await session.commit()
        await session.execute(text("ANALYZE"))
        captured = []

        def capture(_connection, statement, _multi, _parameters, _options):
            if getattr(statement, "is_select", False):
                captured.append(statement)

        event.listen(container.engine.sync_engine, "before_execute", capture)
        try:
            assert await due_retry_ids(session, now) == [edition.id]
            await reconcile_stopped_attempts(session, now)
            assert (
                len(
                    await SqlReportJobRepository(session).list_visible(
                        Visibility(user.id, False, ())
                    )
                )
                == 50
            )
            assert await SqlReportEmbeddingRepository(session).status_counts(
                Visibility(user.id, False, ()), "f" * 64, 1000
            ) == (1000, 1000)
        finally:
            event.remove(container.engine.sync_engine, "before_execute", capture)
        plans = []
        for statement in captured:
            sql = str(
                statement.compile(
                    dialect=container.engine.dialect, compile_kwargs={"literal_binds": True}
                )
            )
            assert "report_jobs.payload," not in sql and "report_embeddings.vector," not in sql
            plan = (await session.scalar(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)))[0]
            indexes = [node["Index Name"] for node in nodes(plan["Plan"]) if "Index Name" in node]
            plans.append(
                {"indexes": indexes, "execution_ms": plan["Execution Time"], "plan": plan["Plan"]}
            )
        assert any(
            "ix_subscription_attempt_history" in item["indexes"]
            or "uq_subscription_attempt_number" in item["indexes"]
            for item in plans
        )
        assert any("ix_subscription_attempt_open" in item["indexes"] for item in plans)
        assert any("ix_report_jobs_owner_created" in item["indexes"] for item in plans)
        print(json.dumps({"attempts": 10000, "jobs": 1000, "embeddings": 1000, "plans": plans}))


async def test_stale_lease_renewal_loses_to_committed_checkpoint(container, user):
    now, token = container.clock.now(), uuid4()
    stored = await saved(
        container.session_factory,
        job(
            owner_id=user.id,
            created_at=now,
            updated_at=now,
            status="running",
            lease_token=token,
            lease_until=now + timedelta(seconds=45),
        ),
    )
    async with container.session_factory() as heartbeat, container.session_factory() as writer:
        stale = await SqlReportJobRepository(heartbeat).get(stored.id)
        current = await SqlReportJobRepository(writer).checkpoint(
            stored.id,
            expected_revision=1,
            lease_token=token,
            payload={"schema_version": 1, "summary": {"completed_sections": 1}},
            stage="drafting",
            now=now,
            lease_until=now + timedelta(seconds=45),
        )
        await writer.commit()
        assert current.revision == 2
        assert not await renew_lease(heartbeat, stale, token, now, now + timedelta(seconds=60))
        await heartbeat.rollback()
        retained = await SqlReportJobRepository(heartbeat).get(stored.id)
        assert retained == current


async def test_projection_retains_valid_totals_larger_than_postgres_int4(container, user):
    now = container.clock.now()
    value = await saved(
        container.session_factory,
        job(
            owner_id=user.id,
            created_at=now,
            updated_at=now,
            payload={
                "schema_version": 1,
                "calls": [
                    {
                        "status": "completed",
                        "reserved_output": 100,
                        "completion_tokens": MAX_COUNTER,
                    }
                    for _ in range(2)
                ],
            },
        ),
    )
    async with container.session_factory() as session:
        total = await session.scalar(
            select(ReportJobUsageRow.subscription_output_tokens).where(
                ReportJobUsageRow.job_id == value.id
            )
        )
        assert total == MAX_COUNTER * 2


@pytest.mark.skipif(os.environ.get("ASE_PERFORMANCE_LOAD") != "1", reason="Opt-in load probe")
async def test_stream_freshness_burst_pool_checkouts(client, container, user):
    identities = [(user, USER_EMAIL)]
    for index in range(1, 8):
        email = f"performance{index}@example.org"
        actor = await create_user(container, email=email, password=USER_PASSWORD)
        identities.append((actor, email))
    claims = [
        container.issuer.verify(await login_token(client, email, USER_PASSWORD))
        for _, email in identities
    ]
    peak = 0
    checkouts = 0
    started = time.perf_counter()

    def checkout(*_args):
        nonlocal peak, checkouts
        peak = max(peak, container.engine.pool.checkedout())
        checkouts += 1

    async def encode(_message):
        return None

    streams = [
        LiveStream(
            container,
            claim,
            deadline=container.clock.now() + timedelta(hours=1),
            expires_in=3600,
            ping_seconds=0.02,
            read_access=lambda claim=claim: _stream_access(claim, container),
            encode=encode,
        ).frames(None)
        for claim in claims
        for _ in range(4)
    ]

    async def stream_checks():
        assert all(
            frame["event"] == "hello"
            for frame in await asyncio.gather(*(anext(stream) for stream in streams))
        )
        for _ in range(3):
            container.clock.advance(timedelta(seconds=31))
            await container.bus.publish(BusMessage("feed.status"))
            async with asyncio.timeout(30):
                await asyncio.gather(*(anext(stream) for stream in streams))

    async def worker_reads():
        for _ in range(3):
            async with container.session_factory() as session:
                await SqlReportJobRepository(session).count_active()
                # Controlled slow query holds a checkout for 25ms.
                await session.execute(text("SELECT pg_sleep(0.025)"))

    event.listen(container.engine.sync_engine, "checkout", checkout)
    try:
        await asyncio.gather(stream_checks(), *(worker_reads() for _ in range(6)))
    finally:
        await asyncio.gather(*(stream.aclose() for stream in streams))
        event.remove(container.engine.sync_engine, "checkout", checkout)
    assert 1 <= peak <= 20
    print(
        json.dumps(
            {
                "stream_freshness_loops": 32,
                "worker_loops": 6,
                "cycles": 3,
                "peak_checkouts": peak,
                "ceiling": 20,
                "checkouts": checkouts,
                "seconds": round(time.perf_counter() - started, 3),
                "timeouts": 0,
                "scope": "32 LiveStream generators, 8 actors, 4 streams each; no HTTP transport",
            }
        )
    )

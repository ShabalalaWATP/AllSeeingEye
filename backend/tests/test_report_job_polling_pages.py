"""Keyset polling reads only compact metadata while preserving all selection filters."""

import re
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, inspect
from sqlalchemy.dialects import postgresql

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.access import Visibility
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from test_report_job_polling_projection import full_summary


def payload(origin="research", *, focus=None, summary=None):
    return {
        "schema_version": 1,
        "input": {"scope": {"origin": origin, "research_focus": focus}},
        "summary": summary if summary is not None else {"completed_sections": 1},
        "evidence": ["x" * 150_000],
    }


async def test_polling_filters_before_limit_without_parsing_checkpoint(job_storage):
    engine, factory = job_storage
    owner, other, team = uuid4(), uuid4(), uuid4()
    requested = await saved(factory, job(owner_id=owner, status="paused"))
    legacy = await saved(
        factory, job(owner_id=other, team_id=team, payload=payload(None, focus="media"))
    )
    for minute in range(1, 6):
        now = NOW + timedelta(minutes=minute)
        await saved(
            factory,
            job(owner_id=owner, status="completed", created_at=now, updated_at=now),
        )
    briefing = await saved(
        factory,
        job(
            owner_id=owner,
            status="paused",
            created_at=NOW + timedelta(hours=1),
            updated_at=NOW + timedelta(hours=1),
            payload=payload("briefing"),
        ),
    )
    await saved(factory, job(owner_id=other, status="paused", payload=payload("briefing")))
    statements = []
    compiled = []

    def capture(_connection, _cursor, statement, _parameters, context, _many):
        statements.append(statement)
        compiled.append(str(context.compiled.statement.compile(dialect=postgresql.dialect())))

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with factory() as session:
            repository = SqlReportJobRepository(session)
            visibility = Visibility(owner, False, (team,))
            rows = await repository.list_page(visibility, limit=1, statuses=("paused",))
            assert [value.id for value in rows] == [requested.id]
            assert len(statements) == 1
            assert all("payload" in inspect(row).unloaded for row in session.identity_map.values())
            all_rows = await repository.list_page(visibility, limit=101, include_briefings=True)
            assert len(all_rows) == 8
            origins = {value.id: value.payload["summary"]["origin"] for value in all_rows}
            assert origins[legacy.id] == "geolocation"
            assert origins[briefing.id] == "briefing"
            assert (
                len(
                    await repository.list_page(
                        Visibility(owner, True, ()), limit=101, include_briefings=True
                    )
                )
                == 9
            )
            assert await repository.list_page(visibility, limit=2, statuses=()) == []
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    assert all(not re.search(r"\breport_jobs\.payload\b", sql) for sql in statements + compiled)
    assert all("report_jobs.summary" in sql for sql in statements + compiled)


async def test_cursor_ties_are_stable_when_new_rows_arrive(job_storage):
    _, factory = job_storage
    owner = uuid4()
    rows = [await saved(factory, job(owner_id=owner)) for _ in range(5)]
    older = await saved(factory, job(owner_id=owner, created_at=NOW - timedelta(seconds=1)))
    expected = [row.id for row in sorted(rows, key=lambda row: row.id)] + [older.id]
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        after = None
        seen = []
        while True:
            page = await repository.list_page(Visibility(owner, False, ()), limit=2, after=after)
            seen += [row.id for row in page]
            if len(page) < 2:
                break
            after = page[-1].created_at, page[-1].id
            now = NOW + timedelta(days=1)
            await repository.add(job(owner_id=owner, created_at=now, updated_at=now))
    assert seen == expected


@pytest.mark.parametrize("limit", [True, 0, -1, 102, 1.0])
async def test_polling_limit_remains_bounded(job_storage, limit):
    _, factory = job_storage
    async with factory() as session:
        with pytest.raises(ValueError):
            await SqlReportJobRepository(session).list_page(
                Visibility(uuid4(), False, ()), limit=limit
            )


async def test_cursor_rejects_naive_time(job_storage):
    _, factory = job_storage
    async with factory() as session:
        with pytest.raises(ValueError):
            await SqlReportJobRepository(session).list_page(
                Visibility(uuid4(), False, ()), limit=1, after=(NOW.replace(tzinfo=None), uuid4())
            )


@pytest.mark.parametrize("origin", ["research", "subscription", "geolocation", "briefing"])
async def test_maximum_original_summary_remains_readable_in_both_polling_apis(job_storage, origin):
    _, factory = job_storage
    value = await saved(factory, job(payload=payload(origin, summary=full_summary())))
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        visibility = Visibility(value.owner_id, False, ())
        page = await repository.list_page(visibility, limit=1, include_briefings=True)
        legacy = await repository.list_visible(visibility)
        assert page[0].payload == legacy[0].payload
        assert page[0].payload["summary"] == {**value.payload["summary"], "origin": origin}
        assert (await repository.get(value.id)).payload == value.payload

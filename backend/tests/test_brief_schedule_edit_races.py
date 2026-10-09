"""Independent SQL writers must not lose settings or subscription execution state."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import JSON, null, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker

from ase.adapters.persistence.models import ScheduleRow
from ase.adapters.persistence.schedules import SqlScheduleRepository
from ase.adapters.persistence.session import create_engine
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_settings import SqlSubscriptionSettings
from ase.application.schedules.definition import ScheduleInput, build_schedule
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.domain.subscription_settings import settings_revision
from test_brief_schedule_editing import settings, subscription
from test_subscription_editions import _edition


async def test_two_independent_editors_cannot_overwrite_each_other(tmp_path, clock):
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'settings.db').as_posix()}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(ScheduleRow.__table__.create)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        original = build_schedule(
            ScheduleInput("Pinned", "intsum", brief_id=uuid4(), brief_revision=1),
            schedule_id=uuid4(),
            owner=uuid4(),
            created=clock.now(),
            now=clock.now(),
        )
        async with factory() as session:
            await SqlScheduleRepository(session).add(original)
            await session.commit()

        async def edit(name):
            async with factory() as session:
                result = await SqlSubscriptionSettings(session).update(
                    original, replace(original, name=name)
                )
                await session.commit()
                return result is not None

        assert sorted(await asyncio.gather(edit("First"), edit("Second"))) == [False, True]
    finally:
        await engine.dispose()


async def test_sql_patch_retains_newer_pause_and_runtime_json(container, client, user):
    row, _, _ = await subscription(client, enabled=True)
    async with container.session_factory() as session:
        original = await SqlScheduleRepository(session).get(UUID(row["id"]))
    later = original.next_run_at + timedelta(days=1)
    async with container.session_factory() as session:
        stored = await session.get(ScheduleRow, original.id)
        stored.enabled = False
        stored.last_run_at = container.clock.now()
        stored.next_run_at = later
        stored.research_options = {
            **stored.research_options,
            "seen_content_signatures": ["fresh-signature"],
        }
        await session.commit()
    async with container.session_factory() as session:
        name_only = await SqlSubscriptionSettings(session).update(
            original, replace(original, name="Renamed")
        )
        await session.commit()
        assert name_only.enabled is False
        assert name_only.next_run_at == later
        assert name_only.seen_content_signatures == ("fresh-signature",)
        edited = replace(
            name_only, monthday=28, cadence="monthly", next_run_at=later + timedelta(days=1)
        )
        saved = await SqlSubscriptionSettings(session).update(name_only, edited)
        await session.commit()
    assert saved.enabled is False
    assert saved.seen_content_signatures == ("fresh-signature",)
    assert saved.last_run_at == container.clock.now()
    assert (saved.monthday, saved.cadence) == (28, "monthly")


async def test_retained_edition_and_frozen_brief_are_unchanged_by_edit(client, container, user):
    row, headers, _ = await subscription(client)
    schedule_id = UUID(row["id"])
    async with container.session_factory() as session:
        original = await SqlScheduleRepository(session).get(schedule_id)
        access = await container.access_policy(session).context(user)
        brief = await load_schedule_brief(session, access, original)
        revision = revision_from_schedule(replace(original, enabled=True), 1, brief=brief)
        ledger = SqlSubscriptionEditionRepository(session)
        await ledger.add_revision(revision)
        edition = await ledger.reserve(_edition(original, revision))
        await session.commit()
    response = await client.put(
        f"/api/schedules/{schedule_id}/brief-settings",
        headers=headers,
        json=settings(row, name="Retained history", cadence="monthly", monthday=31),
    )
    assert response.status_code == 200, response.text
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        assert await ledger.get_revision(schedule_id, 1) == revision
        assert await ledger.history(schedule_id) == [edition]
        current = await SqlScheduleRepository(session).get(schedule_id)
    assert current.brief_id == original.brief_id
    assert current.brief_revision == original.brief_revision
    assert settings_revision(current) != settings_revision(original)


async def test_archive_or_pinned_identity_change_between_read_and_write_cannot_be_overwritten(
    client, container, user
):
    row, _, _ = await subscription(client)
    async with container.session_factory() as session:
        store = SqlSubscriptionSettings(session)
        old = await store.get(UUID(row["id"]))
        await session.execute(
            update(ScheduleRow).where(ScheduleRow.id == old.id).values(brief_revision=2)
        )
        assert await store.update(old, replace(old, name="Must not save")) is None
        await session.rollback()
        await session.execute(
            update(ScheduleRow)
            .where(ScheduleRow.id == old.id)
            .values(archived_at=container.clock.now())
        )
        assert await store.update(old, replace(old, name="Must not save")) is None
        assert (
            await session.scalar(select(ScheduleRow.name).where(ScheduleRow.id == old.id))
            == old.name
        )


async def test_postgresql_update_merges_only_recurrence_json_and_keeps_configuration_fence(clock):
    session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=postgresql.dialect()),
        scalar=AsyncMock(return_value=None),
    )
    original = build_schedule(
        ScheduleInput("Pinned", "intsum", brief_id=uuid4(), brief_revision=1),
        schedule_id=uuid4(),
        owner=uuid4(),
        created=clock.now(),
        now=clock.now(),
    )
    edited = replace(original, monthday=28, cadence="monthly")
    assert await SqlSubscriptionSettings(session).update(original, edited) is None
    statement = session.scalar.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "CAST(coalesce(nullif(CAST(schedules.research_options AS JSONB)" in sql
    assert " || " in sql
    assert {"monthday": 28, "anchor_month": 1} in compiled.params.values()
    changes, predicate = sql.split(" WHERE ")
    assert "enabled=" not in changes and "last_run_at=" not in changes
    assert "archived_at IS NULL" in predicate and "brief_revision =" in predicate


@pytest.mark.parametrize("empty", ["sql_null", "json_null"])
async def test_nullable_historical_options_retain_new_calendar_settings(
    client, container, user, empty
):
    row, headers, _ = await subscription(client)
    async with container.session_factory() as session:
        await session.execute(
            update(ScheduleRow)
            .where(ScheduleRow.id == UUID(row["id"]))
            .values(research_options=null() if empty == "sql_null" else JSON.NULL)
        )
        await session.commit()
    current = (await client.get("/api/schedules", headers=headers)).json()["items"][0]
    edited = await client.put(
        f"/api/schedules/{row['id']}/brief-settings",
        headers=headers,
        json=settings(current, cadence="quarterly", monthday=28, anchor_month=2),
    )
    assert edited.status_code == 200, edited.text
    assert (edited.json()["monthday"], edited.json()["anchor_month"]) == (28, 2)

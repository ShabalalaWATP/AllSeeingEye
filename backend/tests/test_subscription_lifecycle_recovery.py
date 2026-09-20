"""Feed-disabled lifespan keeps one durable subscription admission per due slot."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import func, select

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.app_factory import create_app
from ase.app_lifecycle import lifespan
from ase.application.schedules.manage import ScheduleInput
from helpers import create_user
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT


async def test_feed_disabled_restarts_admit_once_and_stop_all_loops(
    tmp_path, settings, clock, monkeypatch
) -> None:
    database = tmp_path / "feed-disabled-recovery.db"
    local_settings = settings.model_copy(
        update={
            "database_url": f"sqlite+aiosqlite:///{database.as_posix()}",
            "feeds_enabled": False,
        }
    )

    async def idle(*_args) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr("ase.app_lifecycle.expire_original_assets", idle)
    monkeypatch.setattr(
        "ase.app_lifecycle.build_annotation_monitor_worker",
        lambda _container: SimpleNamespace(run=idle),
    )

    first_app = create_app(local_settings, clock=clock)
    first = first_app.state.container
    async with first.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    owner = await create_user(
        first, email="recovery-owner@example.com", password="another-long-passphrase"
    )
    await seed_legacy_profile(first, {**PROFILE, "roles": ["assessment"]})
    async with first.session_factory() as session:
        schedule = await first.create_schedule(session).execute(
            owner,
            ScheduleInput(name="Persistent due slot", template_id="intsum", country_iso="UA"),
            CONTEXT,
        )
    clock.advance(schedule.next_run_at - clock.now() + timedelta(minutes=1))

    async def run_lifespan_once(app):
        container = app.state.container
        container.report_job_worker = AsyncMock()
        container.scheduler = AsyncMock()
        admitted = asyncio.Event()
        original = container.schedule_runner._enqueue_tick

        async def observed_tick() -> int:
            try:
                return await original()
            finally:
                admitted.set()

        container.schedule_runner._enqueue_tick = observed_tick
        async with lifespan(app):
            await asyncio.wait_for(admitted.wait(), timeout=10)
            assert container.schedule_runner._task is not None
            container.scheduler.start.assert_not_awaited()
            async with container.session_factory() as session:
                editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
                jobs = await session.scalar(select(func.count()).select_from(ReportJobRow))
            assert len([item for item in editions if item.job_id is not None]) == 1
            assert jobs == 1
        assert container.schedule_runner._task is None
        assert container.schedule_runner._stopping.is_set()
        container.report_job_worker.stop.assert_awaited_once()
        return editions

    first_editions = await run_lifespan_once(first_app)
    second_app = create_app(local_settings, clock=clock)
    second_editions = await run_lifespan_once(second_app)
    assert [(item.id, item.job_id) for item in second_editions] == [
        (item.id, item.job_id) for item in first_editions
    ]

"""Revision-guarded rule edits reset only their own successful sampling cohort."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select

from ase.adapters.persistence.indicator_baselines import SqlIndicatorBaselines
from ase.adapters.persistence.models import ActivitySampleRow
from ase.domain.errors import Conflict
from assistant_helpers import event
from team_helpers import CONTEXT
from test_indicator_ratios import rule, seed_hours


async def test_stale_revision_never_resets_the_current_cohort(container, user):
    original, data = await rule(container, user)
    await seed_hours(container, original)
    async with container.session_factory() as session:
        saved = await container.update_indicator(session).execute(
            user, original.id, replace(data, name="Renamed"), original.updated_at, CONTEXT
        )
    async with container.session_factory() as session:
        with pytest.raises(Conflict):
            await container.update_indicator(session).execute(
                user,
                original.id,
                replace(data, keywords=("changed",)),
                original.updated_at,
                CONTEXT,
            )
    baselines = SqlIndicatorBaselines(container.session_factory, container.access_policy)
    assert (await baselines.summary(saved, container.clock.now())).sample_hours == 168


async def test_pause_resume_keeps_ratio_configuration_but_excludes_paused_activity(container, user):
    original, data = await rule(container, user, baseline_days=14)
    await seed_hours(container, original)
    before = container.clock.now()
    async with container.session_factory() as session:
        paused = await container.update_indicator(session).execute(
            user, original.id, replace(data, enabled=False), original.updated_at, CONTEXT
        )
    baselines = SqlIndicatorBaselines(container.session_factory, container.access_policy)
    assert (await baselines.summary(paused, before)).sample_hours == 0
    container.clock.advance(timedelta(minutes=10))
    async with container.session_factory() as session:
        resumed = await container.update_indicator(session).execute(
            user, original.id, data, paused.updated_at, CONTEXT
        )
    assert resumed.resumed_at == container.clock.now()
    assert (resumed.baseline_ratio, resumed.baseline_days) == (2, 14)
    container.clock.advance(timedelta(minutes=1))
    now = container.clock.now()
    container.store.upsert(
        [
            replace(event("paused"), published_at=before, observed_at=before),
            replace(event("fresh"), published_at=now, observed_at=now),
        ]
    )
    assert await container.build_evaluator().run_once() == []  # fresh cohort is warming up
    await baselines.record(original, now.replace(minute=0, second=0, microsecond=0), 50)
    async with container.session_factory() as session:
        samples = list(
            await session.scalars(
                select(ActivitySampleRow).where(ActivitySampleRow.key == str(original.id))
            )
        )
    assert len(samples) == 1 and samples[0].value == 1

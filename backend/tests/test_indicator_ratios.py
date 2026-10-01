"""Rule ratios require their own sampled cohort and preserve absolute behaviour."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.baselines import SqlBaselineRepository
from ase.adapters.persistence.indicator_baselines import SqlIndicatorBaselines
from ase.adapters.persistence.models import ActivitySampleRow
from ase.application.warning.indicators import IndicatorInput
from ase.domain.errors import InvalidRequest
from assistant_helpers import event
from team_helpers import CONTEXT


async def rule(container, user, **values):
    data = IndicatorInput("Synthetic ratio", baseline_ratio=2, threshold=3, **values)
    async with container.session_factory() as session:
        created = await container.create_indicator(session).execute(user, data, CONTEXT)
    return created, data


async def seed_hours(container, indicator, count=168, value=2):
    hour = container.clock.now().replace(minute=0, second=0, microsecond=0)
    async with container.session_factory() as session:
        samples = SqlBaselineRepository(session)
        for index in range(1, count + 1):
            await samples.record(
                "indicator", str(indicator.id), hour - timedelta(hours=index), value
            )
        await session.commit()


async def evaluate(container, matches=6):
    container.store.upsert(tuple(event(str(index)) for index in range(matches)))
    return await container.build_evaluator().run_once()


@pytest.mark.parametrize(
    "hours,value,expected", [(167, 2, False), (168, 2, True), (168, 0, False), (168, 4, False)]
)
async def test_warmup_mean_and_ratio(container, user, hours, value, expected):
    indicator, _ = await rule(container, user)
    await seed_hours(container, indicator, hours, value)
    alerts = await evaluate(container)
    assert bool(alerts) is expected
    if expected:
        assert alerts[0].count == 6
        assert alerts[0].baseline_mean == 2 and alerts[0].baseline_ratio == 3
    async with container.session_factory() as session:
        status = await container.indicator_baseline(session).execute(user, indicator.id)
    assert status.sample_hours == hours  # current hour is excluded from its own mean
    assert status.ready is (hours >= 168 and value > 0)


async def test_absolute_rules_and_minimum_count_are_preserved(container, user):
    async with container.session_factory() as session:
        legacy = await container.create_indicator(session).execute(
            user,
            IndicatorInput("Absolute", threshold=2),
            CONTEXT,
        )
    ratio, _ = await rule(container, user)
    await seed_hours(container, ratio, value=1)
    alerts = await evaluate(container, 2)
    assert [alert.indicator_id for alert in alerts] == [legacy.id]


async def test_one_sample_per_hour_and_cooldown(container, user):
    indicator, _ = await rule(container, user)
    await seed_hours(container, indicator)
    assert len(await evaluate(container)) == 1
    assert not await evaluate(container)
    async with container.session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ActivitySampleRow)
            .where(ActivitySampleRow.kind == "indicator")
        )
    assert count == 169


async def test_matching_edit_resets_samples_and_old_inflight_sample_is_rejected(container, user):
    indicator, data = await rule(container, user)
    await seed_hours(container, indicator)
    async with container.session_factory() as session:
        renamed = await container.update_indicator(session).execute(
            user,
            indicator.id,
            replace(data, name="Renamed"),
            indicator.updated_at,
            CONTEXT,
        )
    baselines = SqlIndicatorBaselines(container.session_factory, container.access_policy)
    assert (await baselines.summary(renamed, container.clock.now())).ready
    async with container.session_factory() as session:
        changed = await container.update_indicator(session).execute(
            user,
            indicator.id,
            replace(data, keywords=("changed",)),
            renamed.updated_at,
            CONTEXT,
        )
    await baselines.record(indicator, container.clock.now(), 20)
    assert (await baselines.summary(changed, container.clock.now())).sample_hours == 0
    async with container.session_factory() as session:
        restored = await container.update_indicator(session).execute(
            user, indicator.id, data, changed.updated_at, CONTEXT, confirm_wider_scope=True
        )
    assert (await baselines.summary(restored, container.clock.now())).sample_hours == 0


@pytest.mark.parametrize("values", [{"window_minutes": 360}, {"baseline_days": 6}])
async def test_ratio_configuration_is_validated(container, user, values):
    with pytest.raises(InvalidRequest):
        await rule(container, user, **values)

"""Legacy citation samples cannot be presented as complete consumption history."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.persistence.warning import SqlWarningStore
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.application.warning.indicators import IndicatorInput
from ase.domain.consumed_evidence import MAGIC
from assistant_helpers import event
from team_helpers import CONTEXT
from test_consumed_alert_evidence import create_rule


async def test_legacy_ambiguity_is_explicit_and_post_boundary_activity_still_fires(
    container,
    user,
    clock,
    caplog,
):
    rule = await create_rule(container, user)
    old = clock.now()
    async with container.session_factory() as session:
        session.add(
            WarningConsumptionRow(
                indicator_id=rule.id,
                data=MAGIC,
                count=0,
                expires_at=None,
                legacy_before=old,
            )
        )
        await session.commit()
    container.store.upsert([replace(event(str(i)), published_at=old) for i in range(22)])
    clock.advance(timedelta(minutes=6))
    assert await container.build_evaluator().run_once() == []
    assert any(
        getattr(record, "reason", None) == "legacy_consumption_unavailable"
        for record in caplog.records
    )
    container.store.upsert(
        [replace(event(name), published_at=clock.now()) for name in ("new-a", "new-b")]
    )
    fired = await container.build_evaluator().run_once()
    assert len(fired) == 1 and set(fired[0].event_ids) == {"new-a", "new-b"}
    assert fired[0].count == 2


async def test_expired_legacy_boundary_and_explicit_resume_stop_the_warning(container, user, clock):
    rule = await create_rule(container, user)
    old = clock.now()
    async with container.session_factory() as session:
        session.add(
            WarningConsumptionRow(
                indicator_id=rule.id,
                data=MAGIC,
                count=0,
                expires_at=None,
                legacy_before=old,
            )
        )
        await session.commit()
    data = IndicatorInput(rule.name, threshold=2, cooldown_minutes=5)
    async with container.session_factory() as session:
        paused = await container.update_indicator(session).execute(
            user,
            rule.id,
            replace(data, enabled=False),
            rule.updated_at,
            CONTEXT,
        )
    clock.advance(timedelta(minutes=6))
    async with container.session_factory() as session:
        resumed = await container.update_indicator(session).execute(
            user,
            rule.id,
            data,
            paused.updated_at,
            CONTEXT,
        )
    store = SqlWarningStore(container.session_factory, container.access_policy)
    assert (await store.consumed_evidence(resumed, clock.now())).legacy_before is None
    clock.advance(timedelta(days=7))
    assert (await store.consumed_evidence(resumed, clock.now())).legacy_before is None
    await container.build_evaluator().run_once()
    async with container.session_factory() as session:
        assert await session.get(WarningConsumptionRow, rule.id) is None

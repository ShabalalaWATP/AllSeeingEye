"""Selected-index admission limits on disposable SQLite."""

from uuid import uuid4

import pytest

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.domain.errors import Conflict
from ase.domain.selected_subscription_index import SelectedIndexLimits
from test_selected_subscription_index import NOW, _database, _page, _record, _schedule


@pytest.mark.asyncio
async def test_disabled_schedule_stops_writes_and_source_ceiling_bounds_cursor_state() -> None:
    engine, maker = await _database()
    try:
        owner, subscription_id = uuid4(), uuid4()
        async with maker.begin() as session:
            session.add(_schedule(subscription_id, owner))
        async with maker.begin() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            assert (
                await _page(
                    repo, subscription_id, owner, revision=0, page_key="p1", records=(_record("a"),)
                )
                == 1
            )
            schedule = await session.get(ScheduleRow, subscription_id)
            assert schedule is not None
            schedule.enabled = False
            with pytest.raises(Conflict, match="disabled"):
                await _page(
                    repo,
                    subscription_id,
                    owner,
                    revision=1,
                    page_key="p2",
                    records=(_record("b"),),
                )
            schedule.enabled = True
            with pytest.raises(Conflict, match="source ceiling"):
                await repo.persist_page(
                    subscription_id,
                    "other",
                    actor_id=owner,
                    expected_revision=0,
                    page_key="other1",
                    records=(),
                    cursor_value="other1",
                    watermark_at=NOW,
                    now=NOW,
                    limits=SelectedIndexLimits(sources_per_subscription=1),
                )
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            assert (await repo.get_cursor(subscription_id, "usgs", actor_id=owner)).revision == 1
            assert await repo.get_cursor(subscription_id, "other", actor_id=owner) is None
            assert len(await repo.list_records(subscription_id, actor_id=owner)) == 1
    finally:
        await engine.dispose()

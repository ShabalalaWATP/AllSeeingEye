"""Expiry is enforced without another selected-index acquisition or an active owner."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.selected_index_models import (
    SelectedIndexGateRow,
    SelectedIndexRecordRow,
)
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.container.dormant_retention import DormantRetention
from test_selected_subscription_index import _record, _schedule


@pytest.mark.parametrize("state", ["idle", "paused", "archived", "deactivated"])
async def test_expired_selected_metadata_is_excluded_without_a_new_page(container, user, state):
    now = container.clock.now()
    identifier = uuid4()
    async with container.session_factory() as session:
        session.add(_schedule(identifier, user.id))
        session.add(SelectedIndexGateRow(id=1, revision=0))
        await session.commit()
        repository = SqlSelectedSubscriptionIndexRepository(session)
        await repository.persist_page(
            identifier,
            "usgs",
            actor_id=user.id,
            expected_revision=0,
            page_key="old",
            records=(_record("old", retention_days=1),),
            cursor_value="old",
            watermark_at=None,
            now=now - timedelta(days=2),
        )
        if state == "paused":
            (await session.get(ScheduleRow, identifier)).enabled = False
        elif state == "archived":
            (await session.get(ScheduleRow, identifier)).archived_at = now
        elif state == "deactivated":
            (await session.get(UserRow, user.id)).is_active = False
        await session.commit()
    async with container.session_factory() as session:
        assert (
            await SqlSelectedSubscriptionIndexRepository(session).list_records(
                identifier, actor_id=user.id, now=now
            )
            == ()
        )
    await DormantRetention(container).selected()
    async with container.session_factory() as session:
        assert await session.scalar(select(SelectedIndexRecordRow)) is None

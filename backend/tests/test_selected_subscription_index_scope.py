"""Current membership grants selected-index reads, while owner identity gates writes."""

from uuid import uuid4

import pytest

from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.domain.errors import Forbidden
from test_selected_subscription_index import _database, _page, _record, _schedule


@pytest.mark.asyncio
async def test_team_scope_requires_membership_and_originating_owner_for_page_writes() -> None:
    engine, maker = await _database()
    try:
        owner, team, member, subscription_id = uuid4(), uuid4(), uuid4(), uuid4()
        async with maker.begin() as session:
            session.add(_schedule(subscription_id, owner, team))
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            for actor in (owner, member):
                with pytest.raises(Forbidden):
                    await _page(
                        repo,
                        subscription_id,
                        actor,
                        revision=0,
                        page_key="p1",
                        records=(_record("a"),),
                    )
                with pytest.raises(Forbidden):
                    await repo.list_records(subscription_id, actor_id=actor)
            await session.rollback()
            async with session.begin():
                assert (
                    await _page(
                        repo,
                        subscription_id,
                        owner,
                        team_ids=(team,),
                        revision=0,
                        page_key="p1",
                        records=(_record("a"),),
                    )
                    == 1
                )
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            assert (
                len(
                    await repo.list_records(
                        subscription_id, actor_id=member, authorised_team_ids=(team,)
                    )
                )
                == 1
            )
            with pytest.raises(Forbidden, match="owner"):
                await _page(
                    repo,
                    subscription_id,
                    member,
                    team_ids=(team,),
                    revision=1,
                    page_key="p2",
                    records=(_record("b"),),
                )
            with pytest.raises(Forbidden):
                await repo.get_cursor(subscription_id, "usgs", actor_id=member)
    finally:
        await engine.dispose()

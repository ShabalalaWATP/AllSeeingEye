"""An administrator's persisted source disable applies to an already admitted replan."""

from dataclasses import replace

from httpx import AsyncClient

from ase.application.research.service import ResearchCollectionService
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container import Container
from ase.domain.research import CollectionStatus, ResearchBatch
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_events_api import app  # noqa: F401 (isolated fake source inventory)
from test_research_collection import QUERY, Provider, event


async def test_disabling_source_during_replan_blocks_second_underlying_fetch(
    client: AsyncClient, container: Container, admin: User
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    underlying = Provider("fake_feed")
    controlled = ControlledResearchProvider(underlying, container.source_admission)
    service = ResearchCollectionService(lambda _: [controlled])
    callback_calls = 0

    async def replan(query, first, remaining):
        nonlocal callback_calls
        callback_calls += 1
        assert first.attempts[0].status is CollectionStatus.EMPTY
        response = await client.patch(
            "/api/admin/sources/fake_feed/activation",
            headers=bearer(token),
            json={"enabled": False},
        )
        assert response.status_code == 204
        assert not await container.source_admission.enabled("fake_feed")
        underlying.batch = ResearchBatch(items=(event("must-not-be-released"),))
        return replace(query, terms=("revised",))

    result = await service.collect(QUERY, replan=replan)
    assert callback_calls == underlying.called == 1
    assert result.items == ()
    assert len(result.passes) == 2
    assert result.passes[0].attempts[0].status is CollectionStatus.EMPTY
    assert result.passes[1].attempts[0].status is CollectionStatus.UNAVAILABLE
    assert "disabled by the administrator" in result.passes[1].attempts[0].explanation
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert container.store.stats().total == 0

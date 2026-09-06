"""Progress isolation, bounded capacity and honest immutable terminal states."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.research.runs import ResearchRunStore
from ase.container import Container
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.research_runs import ResearchStage
from ase.domain.users import Role, User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token
from research_input_helpers import NOW, actor


def test_progress_is_private_and_expires_without_retaining_research() -> None:
    clock, user = FakeClock(NOW), actor()
    store = ResearchRunStore(clock)
    run = store.reserve(user, uuid4())
    assert run.stage is ResearchStage.PLANNING
    for other in (
        actor(),
        replace(actor(), role=Role.ADMIN),
        replace(user, security_version=1),
        replace(user, is_active=False),
    ):
        with pytest.raises(NotFound):
            store.read(other, run.id)
    with pytest.raises(NotFound):
        store.reserve(replace(user, is_active=False), uuid4())
    with pytest.raises(InvalidRequest):
        store.reserve(user, run.id)
    store.update(user, run.id, ResearchStage.COLLECTING)
    assert store.read(user, run.id).stage is ResearchStage.COLLECTING
    clock.advance(timedelta(minutes=30))
    with pytest.raises(NotFound):
        store.read(user, run.id)
    assert not store._runs


def test_terminal_progress_cannot_be_overwritten_by_late_cancellation() -> None:
    store, user = ResearchRunStore(FakeClock(NOW)), actor()
    run = store.reserve(user, uuid4())
    for stage, report_id in ((ResearchStage.COMPLETED, None), (ResearchStage.DRAFTING, uuid4())):
        with pytest.raises(ValueError):
            store.update(user, run.id, stage, report_id)
    report_id = uuid4()
    finished = store.update(user, run.id, ResearchStage.COMPLETED, report_id)
    assert finished.report_id == report_id
    assert store.update(user, run.id, ResearchStage.CANCELLED) == finished


def test_capacity_preserves_active_work_and_evicts_only_old_terminal_progress() -> None:
    store, user = ResearchRunStore(FakeClock(NOW)), actor()
    first = store.reserve(user, uuid4())
    store.reserve(user, uuid4())
    with pytest.raises(RateLimited):
        store.reserve(user, uuid4())
    for _ in range(30):
        store.reserve(actor(), uuid4())
    with pytest.raises(RateLimited):
        store.reserve(actor(), uuid4())
    store.update(user, first.id, ResearchStage.FAILED)
    store.reserve(user, uuid4())
    with pytest.raises(NotFound):
        store.read(user, first.id)
    assert len(store._runs) == 32


async def test_progress_endpoint_requires_current_owner(
    client: AsyncClient, container: Container, user: User
) -> None:
    run = container.research_runs.reserve(user, uuid4())
    url = f"/api/research/runs/{run.id}"
    assert (await client.get(url)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get(url, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["stage"] == "planning"
    assert "owner_id" not in response.json() and "security_version" not in response.json()
    assert response.headers["cache-control"] == "no-store"
    foreign = container.research_runs.reserve(actor(), uuid4())
    assert (
        await client.get(f"/api/research/runs/{foreign.id}", headers=bearer(token))
    ).status_code == 404

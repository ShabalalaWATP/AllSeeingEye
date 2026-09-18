"""Concurrent workspace saves serialise revisions and recheck current administration."""

import asyncio
from dataclasses import replace

import pytest

from ase.adapters.persistence.session import create_session_factory
from ase.api.schemas_llm_workspace import LlmWorkspaceChangeIn
from ase.application.dto import RequestContext
from ase.domain.errors import Forbidden, InvalidRequest
from ase.domain.users import Role
from race_database import race_engine
from test_llm_workspace import allowance_change


async def test_concurrent_first_allowance_creates_reject_stale_absence(tmp_path, container, admin):
    engine = await race_engine(tmp_path, "workspace-revisions.db")
    factory = create_session_factory(engine)
    async with factory() as session:
        await container.repositories(session).users.add(admin)
        await session.commit()
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause():
        entered.set()
        await release.wait()

    async def apply(preset, callback=None):
        async with factory() as session:
            try:
                result = await container.llm_workspace(session).execute(
                    admin,
                    [LlmWorkspaceChangeIn.model_validate(allowance_change(preset)).to_input()],
                    RequestContext(None, None),
                    before_save=callback,
                )
                return result.policies[0].request_limit
            except InvalidRequest:
                return "stale"

    try:
        first = asyncio.create_task(apply("light", pause))
        await asyncio.wait_for(entered.wait(), 5)
        second = asyncio.create_task(apply("power"))
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(second), 0.05)
        release.set()
        assert await asyncio.gather(first, second) == [50, "stale"]
        async with factory() as session:
            policies = await container.repositories(session).ai_usage.list_policies()
            assert len(policies) == 1 and policies[0].request_limit == 50
    finally:
        release.set()
        await engine.dispose()


async def test_waiting_workspace_edit_rejects_current_demoted_administrator(
    tmp_path, container, admin
):
    engine = await race_engine(tmp_path, "workspace-admin.db")
    factory = create_session_factory(engine)
    async with factory() as session:
        await container.repositories(session).users.add(admin)
        await session.commit()

    async def apply():
        async with factory() as session:
            await container.llm_workspace(session).execute(
                admin,
                [LlmWorkspaceChangeIn.model_validate(allowance_change("blocked")).to_input()],
                RequestContext(None, None),
            )

    try:
        async with factory() as holder:
            users = container.repositories(holder).users
            await users.lock_administration()
            pending = asyncio.create_task(apply())
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), 0.05)
            await users.save(replace(admin, role=Role.USER))
            await holder.commit()
        with pytest.raises(Forbidden):
            await pending
        async with factory() as session:
            assert await container.repositories(session).ai_usage.list_policies() == []
    finally:
        await engine.dispose()

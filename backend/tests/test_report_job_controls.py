"""Control edge cases retain access restrictions and require explicit, useful resumes."""

from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.dto import RequestContext
from ase.application.report_jobs.views import refresh_summary
from ase.application.reports.request import ReportRequest
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, RateLimited
from ase.domain.teams import MembershipRole, Team, TeamMembership
from report_job_helpers import NOW, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import call
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401

REQUEST = ReportRequest("ask", question="Question")


async def initial(env):
    async with env.service() as (service, deps):
        result = await service.create(
            env.user, uuid4(), REQUEST, RequestContext(), check_session=AsyncMock()
        )
        return await deps.repo.get(result["id"])


@pytest.mark.parametrize("status", ["completed", "needs_review"])
async def test_completed_jobs_cannot_be_paused_or_resumed(service_env, status):
    env = service_env
    original = await initial(env)
    complete = replace(original, id=uuid4(), request_key=uuid4(), status=status, version_id=uuid4())
    await saved(env.factory, complete)
    async with env.service() as (service, _):
        for method in (service.pause, service.resume):
            with pytest.raises(InvalidRequest, match="completed"):
                await method(env.user, complete.id, check_session=AsyncMock())


async def test_repeated_control_requests_are_idempotent(service_env):
    env = service_env
    original = await initial(env)
    async with env.service() as (service, _):
        queued = await service.resume(env.user, original.id, check_session=AsyncMock())
        assert queued["revision"] == 1
        first = await service.pause(env.user, original.id, check_session=AsyncMock())
        again = await service.pause(env.user, original.id, check_session=AsyncMock())
        assert first["revision"] == again["revision"]


async def test_pausing_still_stops_work_when_its_source_is_disabled(service_env):
    class SourceDisabled(InvalidRequest):
        code = "report_job_source_disabled"

    env = service_env
    original = await initial(env)
    async with env.service(check_job=AsyncMock(side_effect=SourceDisabled())) as (service, deps):
        result = await service.pause(env.user, original.id, check_session=AsyncMock())
        assert result["status"] == "paused" and result["sections"] == []
        assert not result["can_resume"] and "source" in result["error"]
        deps.cancel.assert_called_once_with(original.id, None)
        assert (await deps.repo.get(original.id)).status == "paused"
        with pytest.raises(SourceDisabled):
            await service.read(env.user, original.id, check_session=AsyncMock())


async def test_lost_revision_never_reports_control_success(service_env):
    env = service_env
    original = await initial(env)
    async with env.service() as (service, deps):
        deps.repo.pause = AsyncMock(return_value=None)
        with pytest.raises(Conflict):
            await service.pause(env.user, original.id, check_session=AsyncMock())
        deps.cancel.assert_not_called()
    async with env.service() as (service, deps):
        await service.pause(env.user, original.id, check_session=AsyncMock())
        deps.repo.resume = AsyncMock(return_value=None)
        with pytest.raises(Conflict):
            await service.resume(env.user, original.id, check_session=AsyncMock())


async def test_resume_checks_owner_concurrency_and_retains_exhausted_budget(service_env):
    env = service_env
    original = await initial(env)
    paused = replace(original, id=uuid4(), request_key=uuid4(), status="paused", version_id=uuid4())
    await saved(env.factory, paused)
    await initial(env)
    async with env.service() as (service, _):
        with pytest.raises(RateLimited):
            await service.resume(env.user, paused.id, check_session=AsyncMock())
        await service.pause(env.user, original.id, check_session=AsyncMock())
    data = deepcopy(original.payload)
    data["calls"] = [call("uncertain") for _ in range(8)]
    refresh_summary(data)
    exhausted = replace(paused, id=uuid4(), request_key=uuid4(), version_id=uuid4(), payload=data)
    await saved(env.factory, exhausted)
    async with env.service() as (service, _):
        with pytest.raises(InvalidRequest, match="allowance"):
            await service.resume(env.user, exhausted.id, check_session=AsyncMock())


async def team_job(env):
    original = await initial(env)
    team = Team(uuid4(), "Research", True, env.user.id, NOW, NOW)
    async with env.factory() as session:
        repo = SqlTeamRepository(session)
        await repo.add(team)
        for actor in (env.user, env.stranger):
            await repo.put_membership(TeamMembership(team.id, actor.id, MembershipRole.MEMBER, NOW))
        await session.commit()
    shared = replace(
        original,
        id=uuid4(),
        request_key=uuid4(),
        team_id=team.id,
        status="paused",
        version_id=uuid4(),
    )
    await saved(env.factory, shared)
    return shared


async def test_team_member_can_read_partial_work_but_cannot_control_another_owner(service_env):
    env = service_env
    shared = await team_job(env)
    async with env.service() as (service, _):
        result = await service.read(env.stranger, shared.id, check_session=AsyncMock())
        assert not result["can_resume"]
        for method in (service.pause, service.resume):
            with pytest.raises(Forbidden):
                await method(env.stranger, shared.id, check_session=AsyncMock())


@pytest.mark.parametrize("method", ["list", "read"])
async def test_membership_removed_during_read_never_releases_old_scope(service_env, method):
    env = service_env
    shared = await team_job(env)

    async def remove(_):
        async with env.factory() as session:
            await SqlTeamRepository(session).remove_membership(shared.team_id, env.stranger.id)
            await session.commit()

    async with env.service(check_job=remove) as (service, _):
        if method == "list":
            assert await service.list(env.stranger, 20, check_session=AsyncMock()) == []
        else:
            with pytest.raises(NotFound):
                await service.read(env.stranger, shared.id, check_session=AsyncMock())


async def test_source_guard_surrounds_strict_admission_and_control_checks(service_env):
    entered = False

    @asynccontextmanager
    async def guard():
        nonlocal entered
        assert not entered
        entered = True
        try:
            yield
        finally:
            entered = False

    async def checked(_):
        assert entered

    env = service_env
    async with env.service(source_guard=guard, check_job=checked, check_resume=checked) as (
        service,
        _,
    ):
        value = await service.create(
            env.user, uuid4(), REQUEST, RequestContext(), check_session=AsyncMock()
        )
        await service.pause(env.user, value["id"], check_session=AsyncMock())
        await service.resume(env.user, value["id"], check_session=AsyncMock())
        assert len(await service.list(env.user, 20, check_session=AsyncMock())) == 1
    assert not entered

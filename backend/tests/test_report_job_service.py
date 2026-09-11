"""Job admission and controls enforce current ownership, quotas and session validity."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.dto import RequestContext
from ase.application.report_jobs.views import refresh_summary
from ase.application.reports.request import ReportRequest
from ase.domain.errors import (
    Conflict,
    Forbidden,
    InvalidRequest,
    NotFound,
    RateLimited,
    Unauthenticated,
)
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import call, section
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401

REQUEST = ReportRequest("ask", question="What does the evidence show?")
CONTEXT = RequestContext()


async def create(env, **changes):
    async with env.service(**changes) as (service, _):
        return await service.create(env.user, uuid4(), REQUEST, CONTEXT, check_session=AsyncMock())


async def test_create_commits_fixed_ids_and_only_frozen_input(service_env):
    env = service_env
    key = uuid4()
    check = AsyncMock()
    async with env.service() as (service, deps):
        result = await service.create(env.user, key, REQUEST, CONTEXT, check_session=check)
        persisted = await deps.repo.get(result["id"])
        assert persisted.request_key == key and persisted.owner_id == env.user.id
        assert persisted.payload["input"]["report_id"] == str(persisted.report_id)
        assert persisted.version_id != persisted.report_id
        assert result["report_id"] is None and result["sections"] == []
        assert set(persisted.payload) == {
            "schema_version",
            "input",
            "request_digest",
            "sections",
            "calls",
            "collection",
            "summary",
        }
        assert deps.prepare_job.await_count == deps.freeze.call_count == 1
        assert deps.check_resume.await_count == deps.check_job.await_count == 1
        assert check.await_count == 3


async def test_request_replay_is_owner_scoped_and_mismatched_body_conflicts(service_env):
    env, key = service_env, uuid4()
    async with env.service() as (service, deps):
        first = await service.create(env.user, key, REQUEST, CONTEXT, check_session=AsyncMock())
        again = await service.create(env.user, key, REQUEST, CONTEXT, check_session=AsyncMock())
        assert first["id"] == again["id"] and deps.prepare_job.await_count == 1
        other = await service.create(env.stranger, key, REQUEST, CONTEXT, check_session=AsyncMock())
        assert other["id"] != first["id"]
        for changed in (
            replace(REQUEST, question="Another question"),
            replace(REQUEST, research_input_id=uuid4()),
        ):
            with pytest.raises(Conflict):
                await service.create(env.user, key, changed, CONTEXT, check_session=AsyncMock())


async def test_simultaneous_same_request_and_owner_quotas_are_serialised(service_env):
    env, key = service_env, uuid4()

    async def submit(request_id):
        async with env.service() as (service, _):
            return await service.create(
                env.user, request_id, REQUEST, CONTEXT, check_session=AsyncMock()
            )

    results = await asyncio.gather(submit(key), submit(key))
    assert results[0]["id"] == results[1]["id"]
    results = await asyncio.gather(submit(uuid4()), submit(uuid4()), return_exceptions=True)
    assert sum(isinstance(row, RateLimited) for row in results) == 1
    async with env.factory() as session:
        assert await SqlReportJobRepository(session).count_active(env.user.id) == 2


@pytest.mark.parametrize("global_limit", [False, True])
async def test_paused_jobs_still_count_towards_retained_limit(service_env, global_limit):
    env = service_env
    for _ in range(100 if global_limit else 20):
        await saved(
            env.factory,
            job(owner_id=env.stranger.id if global_limit else env.user.id, status="paused"),
        )
    with pytest.raises(InvalidRequest, match="retained"):
        await create(env)


@pytest.mark.parametrize("method", ["read", "pause", "resume"])
async def test_personal_jobs_cannot_be_read_or_controlled_by_other_user(service_env, method):
    env = service_env
    result = await create(env)
    async with env.service() as (service, deps):
        with pytest.raises(NotFound):
            await getattr(service, method)(env.stranger, result["id"], check_session=AsyncMock())
        assert deps.cancel.call_count == 0
        assert await service.list(env.stranger, 20, check_session=AsyncMock()) == []


async def test_account_deactivation_during_source_check_blocks_partial_release(service_env):
    env = service_env
    result = await create(env)

    async def deactivate(_):
        async with env.factory() as session:
            await SqlUserRepository(session).save(replace(env.user, is_active=False))
            await session.commit()

    async with env.service(check_job=deactivate) as (service, _):
        with pytest.raises(Unauthenticated):
            await service.read(env.user, result["id"], check_session=AsyncMock())


@pytest.mark.parametrize("method", ["read", "list"])
async def test_original_session_is_rechecked_after_db_cleanup(service_env, method):
    env = service_env
    result = await create(env)
    async with env.service() as (service, deps):
        calls = 0

        async def expire():
            nonlocal calls
            calls += 1
            if calls == 2:
                assert not deps.session.in_transaction()
                raise Unauthenticated()

        with pytest.raises(Unauthenticated):
            await getattr(service, method)(
                env.user, result["id"] if method == "read" else 20, check_session=expire
            )


async def test_source_denial_blocks_release_and_admission_without_exposing_error(service_env):
    env = service_env
    with pytest.raises(Forbidden):
        await create(env, check_resume=AsyncMock(side_effect=Forbidden()))
    result = await create(env)
    async with env.service(check_job=AsyncMock(side_effect=Forbidden())) as (service, _):
        with pytest.raises(Forbidden):
            await service.read(env.user, result["id"], check_session=AsyncMock())


async def test_pause_cancels_only_committed_old_lease_and_resume_preserves_reservations(
    service_env,
):
    env = service_env
    created = await create(env)
    packet, old_packet, token = "a" * 64, "b" * 64, uuid4()
    async with env.factory() as session:
        repo = SqlReportJobRepository(session)
        claimed = await repo.claim(
            created["id"],
            expected_revision=1,
            lease_token=token,
            now=NOW,
            lease_until=NOW + timedelta(minutes=5),
        )
        payload = deepcopy(claimed.payload)
        payload["current_packet"] = packet
        payload["sections"] = {
            f"{packet}:done": section(packet, "done"),
            f"{packet}:pending": section(packet, "pending", "running"),
            f"{old_packet}:old": section(old_packet, "old", "running"),
        }
        payload["calls"] = [
            call(),
            call(
                "failed",
                completion_tokens=32000,
                error="token_budget_exhausted",
                request_hash="exhausted",
            ),
        ]
        refresh_summary(payload)
        await repo.checkpoint(
            claimed.id,
            expected_revision=claimed.revision,
            lease_token=token,
            payload=payload,
            stage="drafting",
            now=NOW,
        )
        await session.commit()
    async with env.service() as (service, deps):
        paused = await service.pause(env.user, created["id"], check_session=AsyncMock())
        assert paused["status"] == "paused"
        deps.cancel.assert_called_once_with(created["id"], token)
        resumed = await service.resume(env.user, created["id"], check_session=AsyncMock())
        stored = await deps.repo.get(created["id"])
        assert resumed["status"] == "queued" and resumed["usage"]["output_tokens"] == 64000
        assert stored.payload["calls"][0]["status"] == "uncertain"
        assert stored.payload["calls"][1] == payload["calls"][1]
        assert stored.payload["sections"][f"{packet}:done"] == payload["sections"][f"{packet}:done"]
        assert stored.payload["sections"][f"{packet}:pending"]["status"] == "incomplete"
        assert stored.payload["sections"][f"{old_packet}:old"]["status"] == "running"


async def test_expired_session_before_pause_commit_rolls_back_and_does_not_cancel(service_env):
    env = service_env
    result = await create(env)
    check = AsyncMock(side_effect=[None, Unauthenticated()])
    async with env.service() as (service, deps):
        with pytest.raises(Unauthenticated):
            await service.pause(env.user, result["id"], check_session=check)
        assert (await deps.repo.get(result["id"])).status == "queued"
        deps.cancel.assert_not_called()


async def test_changed_profile_paused_job_is_readable_but_resume_is_denied(service_env):
    env = service_env
    result = await create(env)
    async with env.service() as (service, _):
        await service.pause(env.user, result["id"], check_session=AsyncMock())
    async with env.service(
        check_resume=AsyncMock(side_effect=InvalidRequest("Settings changed"))
    ) as (service, _):
        assert (await service.read(env.user, result["id"], check_session=AsyncMock()))[
            "status"
        ] == "paused"
        with pytest.raises(InvalidRequest):
            await service.resume(env.user, result["id"], check_session=AsyncMock())


async def test_bad_preparation_and_missing_jobs_fail_closed(service_env):
    env = service_env
    async with env.service() as (service, deps):
        original = deps.prepare_job.side_effect

        async def mismatch(actor, request):
            value, routing = await original(actor, request)
            return replace(value, actor=env.stranger), routing

        deps.prepare_job.side_effect = mismatch
        with pytest.raises(InvalidRequest):
            await service.create(env.user, uuid4(), REQUEST, CONTEXT, check_session=AsyncMock())
        for method in (service.read, service.pause, service.resume):
            with pytest.raises(NotFound):
                await method(env.user, uuid4(), check_session=AsyncMock())
        for limit in (0, 51, True):
            with pytest.raises(InvalidRequest):
                await service.list(env.user, limit, check_session=AsyncMock())


@pytest.mark.parametrize("failure", [ValueError, TypeError, RecursionError])
async def test_freeze_limits_return_safe_actionable_error_without_admitting_a_job(
    service_env, failure
):
    env = service_env
    async with env.service() as (service, deps):
        deps.freeze.side_effect = failure("INTERNAL SNAPSHOT DETAIL")
        with pytest.raises(InvalidRequest) as error:
            await service.create(env.user, uuid4(), REQUEST, CONTEXT, check_session=AsyncMock())
        assert "Reduce the scope or refresh the inputs" in str(error.value)
        assert "INTERNAL SNAPSHOT DETAIL" not in str(error.value)
        assert await deps.repo.count_active(env.user.id) == 0
        assert await deps.repo.count_open() == 0
        deps.check_resume.assert_not_awaited()
        deps.check_job.assert_not_awaited()
        deps.cancel.assert_not_called()

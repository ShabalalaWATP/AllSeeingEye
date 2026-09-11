"""Discard removes progress only and frees retained-job capacity after authorisation."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from report_job_helpers import NOW, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401
from test_report_job_controls import initial


async def test_other_user_cannot_discard_personal_progress(service_env):
    env = service_env
    original = await initial(env)
    async with env.service() as (service, deps):
        await service.pause(env.user, original.id, check_session=AsyncMock())
        with pytest.raises(NotFound):
            await service.discard(env.stranger, original.id, check_session=AsyncMock())
        assert await deps.repo.get(original.id) is not None


@pytest.mark.parametrize("running", [False, True])
async def test_active_work_requires_pause_before_discard(service_env, running):
    env = service_env
    original = await initial(env)
    if running:
        async with env.factory() as session:
            await SqlReportJobRepository(session).claim(
                original.id,
                expected_revision=1,
                lease_token=uuid4(),
                now=NOW,
                lease_until=NOW + timedelta(minutes=5),
            )
            await session.commit()
    async with env.service() as (service, deps):
        with pytest.raises(InvalidRequest, match="Pause"):
            await service.discard(env.user, original.id, check_session=AsyncMock())
        assert await deps.repo.get(original.id) is not None


async def test_discard_frees_retained_quota_even_if_sources_are_unavailable(service_env):
    env = service_env
    original = await initial(env)
    async with env.service() as (service, _):
        await service.pause(env.user, original.id, check_session=AsyncMock())
    async with env.factory() as session:
        repo = SqlReportJobRepository(session)
        for _ in range(19):
            await repo.add(
                replace(
                    original, id=uuid4(), request_key=uuid4(), version_id=uuid4(), status="failed"
                )
            )
        await session.commit()
    with pytest.raises(InvalidRequest, match="retained"):
        await initial(env)
    async with env.service(
        check_job=AsyncMock(side_effect=InvalidRequest()),
        check_resume=AsyncMock(side_effect=InvalidRequest()),
    ) as (service, deps):
        await service.discard(env.user, original.id, check_session=AsyncMock())
        assert await deps.repo.count_open(env.user.id) == 19
        deps.check_job.assert_not_awaited()
        deps.check_resume.assert_not_awaited()
    assert (await initial(env)).status == "queued"


async def test_discard_completed_progress_keeps_published_report_and_version(service_env):
    env = service_env
    original = await initial(env)
    complete = replace(
        original, id=uuid4(), request_key=uuid4(), version_id=uuid4(), status="completed"
    )
    await saved(env.factory, complete)
    async with env.factory() as session:
        session.add(
            ReportRow(
                id=complete.report_id,
                template="ask",
                title="Published report",
                scope={},
                period_from=NOW - timedelta(days=1),
                period_to=NOW,
                data_cutoff=NOW,
                status="draft",
                created_by=env.user.id,
                created_at=NOW,
                latest_version=1,
            )
        )
        session.add(
            ReportVersionRow(
                id=complete.version_id,
                report_id=complete.report_id,
                number=1,
                status="draft",
                markdown="Saved report",
                model="fixture-model",
                latency_ms=0,
                attempts=1,
                created_at=NOW,
            )
        )
        await session.commit()
    async with env.service() as (service, deps):
        await service.discard(env.user, complete.id, check_session=AsyncMock())
        assert await deps.repo.get(complete.id) is None
    async with env.factory() as session:
        assert await session.get(ReportRow, complete.report_id) is not None
        assert await session.get(ReportVersionRow, complete.version_id) is not None


async def test_discard_expired_session_and_lost_revision_roll_back(service_env):
    env = service_env
    original = await initial(env)
    async with env.service() as (service, deps):
        await service.pause(env.user, original.id, check_session=AsyncMock())
        check = AsyncMock(side_effect=[None, Unauthenticated()])
        with pytest.raises(Unauthenticated):
            await service.discard(env.user, original.id, check_session=check)
        assert await deps.repo.get(original.id) is not None
        await deps.session.rollback()
        deps.repo.discard = AsyncMock(return_value=False)
        with pytest.raises(Conflict):
            await service.discard(env.user, original.id, check_session=AsyncMock())
        with pytest.raises(NotFound):
            await service.discard(env.user, uuid4(), check_session=AsyncMock())


async def test_discard_final_session_check_happens_after_commit(service_env):
    env = service_env
    original = await initial(env)
    async with env.service() as (service, deps):
        await service.pause(env.user, original.id, check_session=AsyncMock())
        checks = 0

        async def session_check():
            nonlocal checks
            checks += 1
            if checks == 3:
                assert not deps.session.in_transaction()
                async with env.factory() as session:
                    assert await SqlReportJobRepository(session).get(original.id) is None

        await service.discard(env.user, original.id, check_session=session_check)
        assert checks == 3

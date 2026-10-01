"""Evaluation run lifecycle edges: shutdown, abandoned runs and unexpected failures."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.dto import RequestContext
from ase.domain.errors import NotFound
from ase.domain.evaluations import EvaluationRun, EvaluationRunStatus, EvaluationStopReason
from evaluation_run_helpers import (
    CORE_CASES,
    SECRET_KEY,
    ScriptedRunGateway,
    artefact,
    evaluation_profile,
    finished,
    start_run,
    unzipped,
)


async def _stored(container, profile, actor_id, **values) -> EvaluationRun:
    now = container.clock.now()
    run = EvaluationRun(
        id=uuid4(),
        actor_id=actor_id,
        profile_id=profile.id,
        profile_name=profile.name,
        model=profile.model,
        profile_fingerprint=profile.config_hash,
        case_ids=(CORE_CASES[0],),
        case_fingerprints={CORE_CASES[0]: "x" * 64},
        max_calls=4,
        status=EvaluationRunStatus.RUNNING,
        created_at=now,
        lease_expires_at=now + timedelta(minutes=5),
    )
    run = replace(run, **values)
    async with container.session_factory() as session:
        await container.evaluation_run_repository(session).add(run)
        await session.commit()
    return run


async def _get(container, run_id) -> EvaluationRun:
    async with container.session_factory() as session:
        found = await container.evaluation_run_repository(session).get(run_id)
    assert found is not None
    return found


async def test_shutdown_records_an_interrupted_run_with_its_partial_artefact(
    container, admin
) -> None:
    profile = await evaluation_profile(container)

    async def wait_forever(count: int) -> None:
        await asyncio.Event().wait()

    container.llm = ScriptedRunGateway(hook=wait_forever)
    run = await start_run(container, admin, profile)
    await asyncio.sleep(0.05)
    container.evaluation_tasks.cancel_all()
    done = await finished(container, admin, run.id)
    assert done.status is EvaluationRunStatus.STOPPED
    assert done.stop_reason is EvaluationStopReason.INTERRUPTED
    files = unzipped(await artefact(container, admin, run.id))
    assert '"status": "interrupted"' in files["results.json"].decode()
    assert not container.evaluation_tasks.cancel(run.id)


async def test_unexpected_errors_stop_the_run_without_logging_their_text(
    container, admin, caplog
) -> None:
    profile = await evaluation_profile(container)

    class Broken(ScriptedRunGateway):
        async def complete(self, base_url, api_key, model, request):
            self.calls.append((base_url, api_key, request.schema_name))
            raise RuntimeError(f"unexpected failure quoting {api_key}")

    container.llm = Broken()
    caplog.set_level(logging.WARNING)
    run = await start_run(container, admin, profile)
    done = await finished(container, admin, run.id)
    assert done.status is EvaluationRunStatus.STOPPED
    assert done.stop_reason is EvaluationStopReason.FAILED
    assert done.calls_reserved == done.calls_failed == 1
    assert SECRET_KEY not in caplog.text


async def test_an_abandoned_run_can_be_cancelled_and_has_no_download(
    container, admin, clock
) -> None:
    profile = await evaluation_profile(container)
    stale = await _stored(
        container, profile, admin.id, lease_expires_at=clock.now() - timedelta(seconds=1)
    )
    async with container.session_factory() as session:
        cancelled = await container.evaluation_runs(session).cancel(
            admin, stale.id, RequestContext()
        )
    assert cancelled.status is EvaluationRunStatus.CANCELLED and cancelled.cancel_requested
    with pytest.raises(NotFound):
        await artefact(container, admin, stale.id)


async def test_execution_respects_finished_and_already_cancelled_runs(container, admin) -> None:
    profile = await evaluation_profile(container)
    gateway = ScriptedRunGateway()
    container.llm = gateway
    flagged = await _stored(container, profile, admin.id, cancel_requested=True)
    await container._execute_evaluation(flagged.id)
    assert (await _get(container, flagged.id)).status is EvaluationRunStatus.CANCELLED
    # A finished or missing run is never executed again.
    await container._execute_evaluation(flagged.id)
    await container._execute_evaluation(uuid4())
    assert gateway.calls == []


async def test_a_run_without_an_owner_is_stopped_before_any_call(container, admin) -> None:
    profile = await evaluation_profile(container)
    gateway = ScriptedRunGateway()
    container.llm = gateway
    orphan = await _stored(container, profile, None)
    await container._execute_evaluation(orphan.id)
    stopped = await _get(container, orphan.id)
    assert stopped.stop_reason is EvaluationStopReason.ACCESS_REVOKED
    assert gateway.calls == [] and not stopped.has_artefact

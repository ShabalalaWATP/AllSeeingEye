"""Evaluation runs use the stored connection, the AI allowance ledger and a durable call cap."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest

from ai_usage_helpers import add_policy, policy, reservations
from ase.application.admin.evaluations import EvaluationStart
from ase.application.dto import RequestContext
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.evaluations import (
    CALLS_PER_CASE,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
)
from ase.domain.users import Role
from evaluation_run_helpers import (
    CORE_CASES,
    SECRET_KEY,
    SECRET_URL,
    ScriptedRunGateway,
    artefact,
    assert_no_secrets,
    evaluation_profile,
    finished,
    start_run,
    unzipped,
)


async def test_selected_cases_run_through_the_allowance_ledger(container, admin) -> None:
    profile = await evaluation_profile(container)
    gateway = ScriptedRunGateway()
    container.llm = gateway
    run = await start_run(container, admin, profile, cases=CORE_CASES, max_calls=8)
    assert run.status is EvaluationRunStatus.RUNNING
    assert run.estimate.calls == 2 * CALLS_PER_CASE
    done = await finished(container, admin, run.id)
    assert done.status is EvaluationRunStatus.COMPLETED and done.stop_reason is None
    assert [item.case_id for item in done.results] == CORE_CASES
    assert {item.case_id: item.fingerprint for item in done.results} == dict(done.case_fingerprints)
    assert done.calls_reserved == len(gateway.calls) == 8
    # The stored connection is used directly; nobody copied its key into a file.
    assert {(url, key) for url, key, _ in gateway.calls} == {(SECRET_URL, SECRET_KEY)}
    ledger = await reservations(container)
    assert len(ledger) == 0 or all(row.purpose.startswith("evaluation:") for row in ledger)
    first = done.results[0]
    assert first.checks["statement_fields"] >= 1
    assert "accuracy" not in json.dumps(dict(first.checks))


async def test_the_ledger_counts_every_metered_call_against_the_administrator(
    container, admin
) -> None:
    await add_policy(container, policy(limit=50, tokens=None))
    profile = await evaluation_profile(container)
    container.llm = ScriptedRunGateway()
    run = await start_run(container, admin, profile, max_calls=8)
    done = await finished(container, admin, run.id)
    rows = await reservations(container)
    assert len(rows) == done.calls_reserved == 4
    assert {row.attribution.user_id for row in rows} == {admin.id}
    assert {row.purpose.split(":")[0] for row in rows} == {"evaluation"}


async def test_the_call_cap_is_reserved_before_dispatch_and_failures_consume_it(
    container, admin
) -> None:
    await add_policy(container, policy(limit=50, tokens=None))
    profile = await evaluation_profile(container)
    gateway = ScriptedRunGateway(fail=True)
    container.llm = gateway
    run = await start_run(container, admin, profile, cases=CORE_CASES, max_calls=1)
    done = await finished(container, admin, run.id)
    assert done.status is EvaluationRunStatus.STOPPED
    assert done.stop_reason is EvaluationStopReason.CALL_CAP
    assert len(gateway.calls) == done.calls_reserved == done.calls_failed == 1
    rows = await reservations(container)
    # The failed request was dispatched, so the ledger counts it rather than releasing it.
    assert len(rows) == 1 and rows[0].ok is False and rows[0].dispatched_at is not None


async def test_an_exhausted_allowance_policy_stops_the_run(container, admin) -> None:
    await add_policy(container, policy(limit=1, tokens=None))
    profile = await evaluation_profile(container)
    gateway = ScriptedRunGateway()
    container.llm = gateway
    run = await start_run(container, admin, profile, max_calls=8)
    done = await finished(container, admin, run.id)
    assert done.status is EvaluationRunStatus.STOPPED
    assert done.stop_reason is EvaluationStopReason.ALLOWANCE
    assert len(gateway.calls) == 1
    assert done.calls_reserved == 2  # the refused attempt still consumed the run cap


async def test_cancelling_mid_run_stops_before_the_next_call(container, admin) -> None:
    profile = await evaluation_profile(container)
    holder: dict[str, Any] = {}

    async def cancel() -> None:
        async with container.session_factory() as session:
            await container.evaluation_runs(session).cancel(
                admin, holder["run"].id, RequestContext()
            )

    async def cancel_on_second_call(count: int) -> None:
        if count == 2:
            # An administrator's request cancels the run while its provider call waits.
            holder["cancel"] = asyncio.create_task(cancel())
            await asyncio.Event().wait()

    gateway = ScriptedRunGateway(hook=cancel_on_second_call)
    container.llm = gateway
    holder["run"] = await start_run(container, admin, profile, cases=CORE_CASES)
    done = await finished(container, admin, holder["run"].id)
    assert done.status is EvaluationRunStatus.CANCELLED
    assert done.cancel_requested and len(gateway.calls) == 2
    assert done.results == ()
    files = unzipped(await artefact(container, admin, done.id))
    results = json.loads(files["results.json"])
    assert results["status"] == "interrupted" and results["active_case"] == CORE_CASES[0]


async def test_a_durable_cancel_from_another_process_stops_the_next_call(container, admin) -> None:
    profile = await evaluation_profile(container)
    holder: dict[str, EvaluationRun] = {}

    async def flag_only(count: int) -> None:
        if count == 1:
            # Another process sets the flag; this process's task is not cancelled.
            async with container.session_factory() as session:
                await container.evaluation_run_repository(session).request_cancel(holder["run"].id)
                await session.commit()

    gateway = ScriptedRunGateway(hook=flag_only)
    container.llm = gateway
    holder["run"] = await start_run(container, admin, profile, cases=CORE_CASES)
    done = await finished(container, admin, holder["run"].id)
    assert done.status is EvaluationRunStatus.CANCELLED
    assert len(gateway.calls) == done.calls_reserved == 1


async def test_only_one_run_can_be_active(container, admin) -> None:
    profile = await evaluation_profile(container)
    release = asyncio.Event()

    async def wait(count: int) -> None:
        await release.wait()

    container.llm = ScriptedRunGateway(hook=wait)
    first = await start_run(container, admin, profile)
    await asyncio.sleep(0)
    with pytest.raises(Conflict):
        await start_run(container, admin, profile)
    # The database refuses a second active slot even if the service check were skipped.
    async with container.session_factory() as session:
        clone = await container.evaluation_run_repository(session).get(first.id)
        assert clone is not None
        clone.id = uuid4()
        with pytest.raises(Conflict):
            await container.evaluation_run_repository(session).add(clone)
    release.set()
    await finished(container, admin, first.id)
    second = await start_run(container, admin, profile)
    assert (await finished(container, admin, second.id)).status is EvaluationRunStatus.COMPLETED


async def test_an_abandoned_run_is_released_after_its_lease(container, admin, clock) -> None:
    profile = await evaluation_profile(container)
    container.llm = ScriptedRunGateway()
    async with container.session_factory() as session:
        stale = EvaluationRun(
            id=uuid4(),
            actor_id=admin.id,
            profile_id=profile.id,
            profile_name=profile.name,
            model=profile.model,
            profile_fingerprint=profile.config_hash,
            case_ids=(CORE_CASES[0],),
            case_fingerprints={CORE_CASES[0]: "x" * 64},
            max_calls=4,
            status=EvaluationRunStatus.RUNNING,
            created_at=clock.now() - timedelta(hours=1),
            lease_expires_at=clock.now() - timedelta(minutes=1),
        )
        await container.evaluation_run_repository(session).add(stale)
        await session.commit()
    run = await start_run(container, admin, profile)
    await finished(container, admin, run.id)
    async with container.session_factory() as session:
        old = await container.evaluation_runs(session).get(admin, stale.id)
    assert old.status is EvaluationRunStatus.STOPPED
    assert old.stop_reason is EvaluationStopReason.INTERRUPTED


@pytest.mark.parametrize("change", ["connection", "demotion"])
async def test_changes_during_model_work_are_rechecked_before_persistence(
    container, admin, change
) -> None:
    profile = await evaluation_profile(container)

    async def mutate(count: int) -> None:
        if count != 1:
            return
        async with container.session_factory() as session:
            repos = container.repositories(session)
            if change == "connection":
                current = await repos.llm_profiles.get(profile.id)
                current.model = "another-model"
                current.revision += 1
                await repos.llm_profiles.save(current)
            else:
                current = await repos.users.get_by_id(admin.id)
                current.role = Role.USER
                await repos.users.save(current)
            await session.commit()

    container.llm = ScriptedRunGateway(hook=mutate)
    run = await start_run(container, admin, profile, cases=CORE_CASES)
    await container.evaluation_tasks.drain()
    async with container.session_factory() as session:
        done = await container.evaluation_run_repository(session).get(run.id)
    expected = (
        EvaluationStopReason.CONNECTION_CHANGED
        if change == "connection"
        else EvaluationStopReason.ACCESS_REVOKED
    )
    assert done.status is EvaluationRunStatus.STOPPED and done.stop_reason is expected
    assert done.results == () and not done.has_artefact


async def test_summaries_and_artefacts_never_contain_connection_secrets(container, admin) -> None:
    profile = await evaluation_profile(container)
    container.llm = ScriptedRunGateway()
    run = await start_run(container, admin, profile)
    done = await finished(container, admin, run.id)
    content = await artefact(container, admin, run.id)
    files = unzipped(content)
    assert set(files) == {"results.json", "review.json", f"{CORE_CASES[0]}.md"}
    assert_no_secrets(content, *files.values(), repr(done).encode())
    results = json.loads(files["results.json"])
    assert results["connection"]["model"] == "fixture-model"
    assert "base_url" not in results["connection"]
    assert results["cases"][0]["case_sha256"] == done.case_fingerprints[CORE_CASES[0]]
    assert "not accuracy" in results["notice"]


async def test_provider_errors_quoting_secrets_are_not_saved(container, admin) -> None:
    profile = await evaluation_profile(container)
    container.llm = ScriptedRunGateway(fail=True, leak_secrets=True)
    run = await start_run(container, admin, profile, max_calls=2)
    await finished(container, admin, run.id)
    content = await artefact(container, admin, run.id)
    assert_no_secrets(content, *unzipped(content).values())


async def test_start_validates_the_selection_and_connection(container, admin) -> None:
    profile = await evaluation_profile(container)
    embeddings = await evaluation_profile(container, name="Embeddings", roles=("embeddings",))
    with pytest.raises(InvalidRequest):
        await start_run(container, admin, profile, cases=["not_a_case"])
    with pytest.raises(InvalidRequest):
        await start_run(container, admin, profile, cases=[CORE_CASES[0], CORE_CASES[0]])
    with pytest.raises(InvalidRequest):
        await start_run(container, admin, profile, max_calls=0)
    with pytest.raises(InvalidRequest):
        await start_run(container, admin, embeddings)
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.evaluation_runs(session).start(
                admin, EvaluationStart(uuid4(), CORE_CASES[:1], 4), RequestContext()
            )

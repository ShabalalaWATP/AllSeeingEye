"""Observed stages, cancellation cleanup and terminal run receipts."""

import asyncio
import json
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from ase.adapters.persistence.llm import SqlLlmUsageRepository
from ase.adapters.persistence.models import LlmUsageRow, ReportRow
from ase.api.report_run import run_generation
from ase.application.ports.feeds import EventQuery
from ase.application.reports.production import Producer
from ase.domain.llm import LlmUsage
from ase.domain.research_runs import ResearchStage
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from production_integration_helpers import RecordingUsage, StageGateway, production_job
from report_documents_helpers import document_records
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body


def request_boundary(disconnected=False):
    request = AsyncMock()

    async def receive():
        if not disconnected:
            await asyncio.Event().wait()
        return {"type": "http.disconnect"}

    request.receive.side_effect = receive
    return request


async def test_progress_marks_success_only_after_work_returns(container, user):
    request = request_boundary()
    run_id = uuid4()
    record, version = document_records(user.id)

    async def work(progress):
        await progress(ResearchStage.DRAFTING)
        assert container.research_runs.read(user, run_id).stage is ResearchStage.DRAFTING
        await progress(ResearchStage.SAVING)
        assert container.research_runs.read(user, run_id).report_id is None
        return record, version

    assert await run_generation(request, user, container.research_runs, run_id, work) == (
        record,
        version,
    )
    saved = container.research_runs.read(user, run_id)
    assert saved.stage is ResearchStage.COMPLETED and saved.report_id == record.id


@pytest.mark.parametrize("reason", ["disconnect", "deadline", "failure", "cancel"])
async def test_failed_or_cancelled_work_cleans_up_before_terminal_state(
    container, user, monkeypatch, reason
):
    request = request_boundary(reason == "disconnect")
    monkeypatch.setattr("ase.api.report_run.GENERATION_TIMEOUT_SECONDS", 0.02)
    run_id, entered, cleaned = uuid4(), asyncio.Event(), asyncio.Event()

    async def work(progress):
        entered.set()
        try:
            if reason == "failure":
                raise ValueError("controlled error")
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    task = asyncio.create_task(run_generation(request, user, container.research_runs, run_id, work))
    await entered.wait()
    if reason == "cancel":
        task.cancel()
    expected = (
        ValueError
        if reason == "failure"
        else asyncio.CancelledError
        if reason == "cancel"
        else HTTPException
    )
    with pytest.raises(expected):
        await task
    assert cleaned.is_set()
    expected_stage = {"failure": ResearchStage.FAILED, "deadline": ResearchStage.TIMED_OUT}.get(
        reason, ResearchStage.CANCELLED
    )
    assert container.research_runs.read(user, run_id).stage is expected_stage


async def test_simultaneous_disconnect_and_completed_work_keeps_completed(container, user):
    request = request_boundary(True)
    record, version = document_records(user.id)
    run_id = uuid4()

    async def work(progress):
        return record, version

    result = await run_generation(request, user, container.research_runs, run_id, work)
    assert result == (record, version)
    assert container.research_runs.read(user, run_id).stage is ResearchStage.COMPLETED


async def test_commit_that_finishes_while_cancellation_arrives_keeps_its_result(container, user):
    request = request_boundary(True)
    record, version = document_records(user.id)

    async def work(progress):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            # A transaction adapter may finish a commit before the cancellation is observed.
            return record, version

    run_id = uuid4()
    assert await run_generation(request, user, container.research_runs, run_id, work) == (
        record,
        version,
    )
    assert container.research_runs.read(user, run_id).stage is ResearchStage.COMPLETED


async def test_progress_is_optional_and_expired_receipt_does_not_cancel_work(
    container, user, clock
):
    request = request_boundary()
    record, version = document_records(user.id)

    async def work(progress):
        await progress(ResearchStage.DRAFTING)
        return record, version

    assert await run_generation(request, user, container.research_runs, None, work) == (
        record,
        version,
    )

    async def expired(progress):
        clock.advance(timedelta(minutes=31))
        await progress(ResearchStage.DRAFTING)
        return record, version

    assert await run_generation(request, user, container.research_runs, uuid4(), expired) == (
        record,
        version,
    )


async def test_producer_stages_are_observed_and_saving_precedes_final_authorisation(
    container, user
):
    job = production_job(user, container.cipher)
    stages = []
    usage = RecordingUsage()

    async def progress(stage):
        assert not usage.rows
        stages.append(stage)

    async def profile_for(role):
        return job.profile

    async def authorised():
        assert stages[-1] is ResearchStage.VALIDATING

    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=StageGateway(),
        usage=usage,
    )
    await producer.produce(job, profile_for, authorised, progress=progress)
    assert stages == [
        ResearchStage.PLANNING,
        ResearchStage.DRAFTING,
        ResearchStage.CHALLENGING,
        ResearchStage.VALIDATING,
        ResearchStage.SAVING,
    ]


async def test_create_and_regenerate_expose_optional_progress_header(
    client, container, admin, user
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, PROFILE)
    container.store.upsert(tuple(filled_store().query(EventQuery(limit=10))))
    container.llm = ScriptedGateway(json.dumps(good_body()), json.dumps(good_body()))
    run_id = uuid4()
    headers = {**bearer(token), "X-Research-Run-ID": str(run_id)}
    response = await client.post("/api/reports", json={"template": "intsum"}, headers=headers)
    assert response.status_code == 201, response.text
    report_id = response.json()["report"]["id"]
    receipt = await client.get(f"/api/research/runs/{run_id}", headers=bearer(token))
    assert receipt.json()["stage"] == "completed" and receipt.json()["report_id"] == report_id
    duplicate = await client.post("/api/reports", json={"template": "intsum"}, headers=headers)
    assert duplicate.status_code == 422
    second_id = uuid4()
    again = await client.post(
        f"/api/reports/{report_id}/versions",
        headers={**bearer(token), "X-Research-Run-ID": str(second_id)},
    )
    assert again.status_code == 201, again.text
    assert container.research_runs.read(user, second_id).stage is ResearchStage.COMPLETED


async def test_real_asgi_disconnect_cancels_model_and_leaves_no_report_or_usage(
    app, client, container, admin, user
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, PROFILE)
    entered, cleaned = asyncio.Event(), asyncio.Event()

    class WaitingGateway:
        async def complete(self, *args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()

    container.llm = WaitingGateway()
    run_id = uuid4()
    payload = json.dumps({"template": "intsum"}).encode()
    messages = asyncio.Queue()
    messages.put_nowait({"type": "http.request", "body": payload, "more_body": False})
    sent = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/reports",
        "raw_path": b"/api/reports",
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"authorization", f"Bearer {token}".encode()),
            (b"x-research-run-id", str(run_id).encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }
    running = asyncio.create_task(app(scope, messages.get, send))
    await asyncio.wait_for(entered.wait(), timeout=2)
    messages.put_nowait({"type": "http.disconnect"})
    await asyncio.wait_for(running, timeout=2)
    assert cleaned.is_set()
    assert container.research_runs.read(user, run_id).stage is ResearchStage.CANCELLED
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportRow)) == 0
        assert await session.scalar(select(func.count()).select_from(LlmUsageRow)) == 0


async def test_deadline_during_uncommitted_writes_rolls_back_with_request_session(
    container, user, monkeypatch
):

    monkeypatch.setattr("ase.api.report_run.GENERATION_TIMEOUT_SECONDS", 0.2)
    request = request_boundary()
    async with container.session_factory() as session:

        async def work(progress):
            await progress(ResearchStage.SAVING)
            await SqlLlmUsageRepository(session).add(
                LlmUsage(
                    container.clock.now(),
                    uuid4(),
                    user.id,
                    "test-uncommitted",
                    True,
                    0,
                )
            )
            await asyncio.Event().wait()

        with pytest.raises(HTTPException) as stopped:
            await run_generation(request, user, container.research_runs, uuid4(), work)
        assert stopped.value.status_code == 504
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(LlmUsageRow)) == 0

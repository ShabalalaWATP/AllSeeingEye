"""Durable API admission, background publication and the late-pause commit fence."""

import asyncio
from uuid import UUID, uuid4

from ase.application.ports.llm import LlmGatewayError
from ase.application.reports.generate import GenerateReportUseCase
from helpers import CSRF_COOKIE
from report_job_api_helpers import job_settings, prepared, stored, submit, work

__all__ = ["job_settings"]


async def test_enqueue_then_worker_publishes_one_report_with_completed_sections(
    client, user, container
):
    gateway, headers = await prepared(container, client)
    response = await submit(client, headers)
    queued = response.json()
    assert queued["status"] == "queued" and not gateway.calls
    assert response.headers["cache-control"] == "private, no-store"
    assert queued["report_id"] is None
    await work(container)
    current = await stored(container, queued["id"])
    # The synthetic evidence is a two-word summary, so the citation gate asks for review.
    assert current.status == "needs_review", (current.status, current.error, current.payload)
    response = await client.get(f"/api/report-jobs/{queued['id']}", headers=headers)
    assert response.status_code == 200, response.text
    completed = response.json()
    assert completed["status"] == "needs_review" and completed["completed_sections"] == 6
    assert completed["usage"]["calls"] == len(gateway.calls) == 7
    assert completed["usage"]["output_tokens"] == 35
    sections = {section["id"]: section for section in completed["sections"]}
    assert len(sections) == 6 and "synthesis" not in sections
    assert sections["synthesis_judgements"]["reporting"]
    assert sections["synthesis_context"]["assessment"]
    assert "synthetic-job-key" not in response.text and "encrypted" not in response.text
    async with container.session_factory() as session:
        repo = container.repositories(session).reports
        record = await repo.get(UUID(completed["report_id"]))
        version = await repo.get_version(record.id, 1)
    assert record.created_by == user.id and version.id == current.version_id
    assert version.body.cited_labels() <= {item.label for item in version.evidence}
    assert version.prompt_tokens == 70 and version.completion_tokens == 35
    assert "Original reporting from" in version.markdown
    async with container.session_factory() as session:
        usage = await container.repositories(session).llm_usage.list_recent(20)
    assert len(usage) == 7 and sum(row.completion_tokens for row in usage) == 35
    discarded = await client.delete(f"/api/report-jobs/{queued['id']}", headers=headers)
    assert discarded.status_code == 204 and await stored(container, queued["id"]) is None
    async with container.session_factory() as session:
        repo = container.repositories(session).reports
        assert await repo.get(record.id) is not None
        assert (await repo.get_version(record.id, 1)).id == version.id


async def test_repeated_request_uuid_admits_one_job_and_only_one_worker_run(
    client, user, container
):
    gateway, headers = await prepared(container, client)
    request_id = uuid4()
    first = await submit(client, headers, request_id=request_id)
    second = await submit(client, headers, request_id=request_id)
    assert first.json()["id"] == second.json()["id"]
    jobs = await client.get("/api/report-jobs", headers=headers)
    assert jobs.status_code == 200 and len(jobs.json()["items"]) == 1
    await work(container)
    again = await submit(client, headers, request_id=request_id)
    assert again.json()["id"] == first.json()["id"] and again.json()["status"] == "needs_review"
    assert len(gateway.calls) == 7


async def test_pause_after_generation_prevents_report_commit_even_if_cancel_callback_is_lost(
    client,
    user,
    container,
    monkeypatch,
):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    ready, release = asyncio.Event(), asyncio.Event()
    original = GenerateReportUseCase.produce_prepared

    async def after_generation(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        ready.set()
        await release.wait()
        return result

    monkeypatch.setattr(GenerateReportUseCase, "produce_prepared", after_generation)
    worker = container.report_job_worker
    monkeypatch.setattr(worker, "cancel", lambda *_args: None)
    await worker.tick()
    await asyncio.wait_for(ready.wait(), 15)
    response = await client.post(f"/api/report-jobs/{job_id}/pause", headers=headers)
    assert response.status_code == 200 and response.json()["status"] == "paused", response.text
    release.set()
    await asyncio.wait_for(asyncio.gather(*(task for _, task in worker._running.values())), 15)
    current = await stored(container, job_id)
    assert current.status == "paused" and len(gateway.calls) == 7
    async with container.session_factory() as session:
        assert await container.repositories(session).reports.get(current.report_id) is None


async def test_admitted_job_continues_after_original_browser_logout(client, user, container):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    logout = await client.post(
        "/api/auth/logout", headers={"X-CSRF-Token": client.cookies[CSRF_COOKIE]}
    )
    assert logout.status_code == 204
    await work(container)
    current = await stored(container, job_id)
    assert current.status == "needs_review" and len(gateway.calls) == 7
    response = await client.get(f"/api/report-jobs/{job_id}", headers=headers)
    assert response.status_code == 401


async def test_explicit_resume_reuses_completed_topic_and_frozen_collection(
    client, user, container
):
    gateway, headers = await prepared(
        container, client, fail={"S2": LlmGatewayError("unavailable")}
    )
    job_id = (await submit(client, headers)).json()["id"]
    await work(container)
    first = await client.get(f"/api/report-jobs/{job_id}", headers=headers)
    assert first.status_code == 200, first.text
    paused = first.json()
    assert paused["status"] == "paused" and paused["can_resume"]
    assert paused["completed_sections"] == 1
    assert [name for name, _ in gateway.calls] == ["S1", "S2"]
    checkpoint = await stored(container, job_id)
    collection = checkpoint.payload["collection"]
    completed_topic = next(
        row for row in checkpoint.payload["sections"].values() if row["section_id"] == "S1"
    )
    gateway.fail.clear()
    response = await client.post(f"/api/report-jobs/{job_id}/resume", headers=headers)
    assert response.status_code == 202 and response.json()["status"] == "queued", response.text
    await work(container)
    final = await stored(container, job_id)
    assert final.status == "needs_review", final.error
    assert final.payload["collection"] == collection
    assert completed_topic in final.payload["sections"].values()
    assert [name for name, _ in gateway.calls] == [
        "S1",
        "S2",
        "S2",
        "S3",
        "S4",
        "synthesis_judgements",
        "synthesis_context",
        "claims",
    ]
    assert len(final.payload["calls"]) == 8

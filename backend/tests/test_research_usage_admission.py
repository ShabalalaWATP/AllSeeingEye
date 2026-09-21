"""Real durable report admission charges a run once and never refunds discarded work."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.dto import RequestContext
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.research_usage import ResearchUsageLimit
from llm_fixture_helpers import seed_legacy_profile
from report_documents_helpers import document_records
from report_helpers import PROFILE
from report_job_api_helpers import job_settings, prepared, submit, work

__all__ = ["job_settings"]


async def _usage(container, user):
    async with container.session_factory() as session:
        return await container.research_usage(session).me(user)


async def test_replay_pause_resume_and_worker_subcalls_use_one_run(client, container, user):
    gateway, headers = await prepared(container, client)
    request_id = uuid4()
    first = await submit(client, headers, request_id=request_id)
    replay = await submit(client, headers, request_id=request_id)
    assert replay.json()["id"] == first.json()["id"]
    job_id = first.json()["id"]
    assert (await _usage(container, user)).used == 1
    assert (
        await client.post(f"/api/report-jobs/{job_id}/pause", headers=headers)
    ).status_code == 200
    assert (
        await client.post(f"/api/report-jobs/{job_id}/resume", headers=headers)
    ).status_code == 202
    await work(container)
    assert len(gateway.calls) == 10
    assert (await _usage(container, user)).used == 1
    assert (await client.delete(f"/api/report-jobs/{job_id}", headers=headers)).status_code == 204
    assert (await _usage(container, user)).used == 1


async def test_regeneration_is_a_new_run_and_failure_is_not_refunded(container, user, monkeypatch):
    await seed_legacy_profile(container, PROFILE)
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
        generator = container.generate_report(session)

        async def fail(*args, **kwargs):
            assert not session.in_transaction()
            raise InvalidRequest("Synthetic regeneration failure")

        monkeypatch.setattr(generator._producer, "produce_with_claims", fail)
        with pytest.raises(InvalidRequest, match="Synthetic regeneration"):
            await generator.regenerate(user, record.id, RequestContext())
    assert (await _usage(container, user)).used == 1


async def test_discard_cannot_refill_allowance_and_denial_has_reset_header(client, container, user):
    gateway, headers = await prepared(container, client)
    for _ in range(4):
        queued = (await submit(client, headers)).json()
        assert (
            await client.post(f"/api/report-jobs/{queued['id']}/pause", headers=headers)
        ).status_code == 200
        assert (
            await client.delete(f"/api/report-jobs/{queued['id']}", headers=headers)
        ).status_code == 204
    denied = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "report": {"template": "intsum"},
        },
    )
    assert denied.status_code == 429, denied.text
    assert denied.json()["error"]["code"] == "research_usage_limit"
    assert int(denied.headers["retry-after"]) > 0
    assert "UTC" in denied.json()["error"]["message"]
    assert (await _usage(container, user)).used == 4
    assert gateway.calls == []


async def test_validation_and_queue_rejection_do_not_charge(client, container, user):
    _, headers = await prepared(container, client)
    invalid = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "report": {"template": "ask"},
        },
    )
    assert invalid.status_code == 422
    assert (await _usage(container, user)).used == 0
    await submit(client, headers)
    await submit(client, headers)
    capacity = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "report": {"template": "intsum"},
        },
    )
    assert capacity.status_code == 429
    assert capacity.json()["error"]["code"] == "rate_limited"
    assert (await _usage(container, user)).used == 2


async def test_job_storage_failure_rolls_back_research_charge(client, container, user, monkeypatch):
    _, headers = await prepared(container, client)
    monkeypatch.setattr(
        SqlReportJobRepository,
        "add",
        AsyncMock(side_effect=InvalidRequest("Synthetic storage failure")),
    )
    response = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "report": {"template": "intsum"},
        },
    )
    assert response.status_code == 422
    assert (await _usage(container, user)).used == 0


async def test_concurrent_last_slot_and_account_isolation(container, admin, user):
    async def admit(actor):
        async with container.session_factory() as session:
            await container.research_usage(session).admit(actor, None)

    for _ in range(3):
        await admit(user)
    results = await asyncio.gather(admit(user), admit(user), return_exceptions=True)
    assert results.count(None) == 1
    assert sum(isinstance(result, ResearchUsageLimit) for result in results) == 1
    assert (await _usage(container, user)).used == 4
    await admit(admin)
    assert (await _usage(container, admin)).used == 1


async def test_preparation_alone_is_free_and_sync_failure_keeps_charge(
    container, user, monkeypatch
):
    await seed_legacy_profile(container, PROFILE)
    async with container.session_factory() as session:
        generator = container.generate_report(session)
        request = ReportRequest("ask", question="What has changed?")
        await generator.prepare_job(user, request)
        assert (await container.research_usage(session).me(user)).used == 0
        await session.rollback()

        async def fail(*args, **kwargs):
            assert not session.in_transaction()
            raise InvalidRequest("Synthetic production failure")

        monkeypatch.setattr(generator._producer, "produce_with_claims", fail)
        with pytest.raises(InvalidRequest, match="Synthetic production"):
            await generator.execute(user, request, RequestContext())
    assert (await _usage(container, user)).used == 1

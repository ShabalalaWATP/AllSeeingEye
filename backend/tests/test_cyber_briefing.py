"""Cyber briefing windows freeze independently and retain daily admission protection."""

from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.cyber_briefing import cyber_briefing_request
from ase.application.feeds.budgets import budget_for
from ase.domain.cyber import CYBER_BRIEFING_PUBLISHER_IDS, CYBER_PUBLISHER_IDS, CyberWindowDays
from ase.domain.daily_briefing import (
    cyber_briefing_key,
    economy_briefing_key,
    retains_daily_admission,
)
from ase.domain.events import Category
from ase.domain.research import ResearchBatch, ResearchMode, ResearchQuery
from feeds_helpers import make_event
from report_job_api_helpers import job_settings, prepared, stored, work
from report_job_helpers import NOW, job

__all__ = ["job_settings"]


@pytest.mark.parametrize("days", CyberWindowDays)
def test_request_uses_only_reviewed_publishers_and_names_exact_interval(days):
    request = cyber_briefing_request(days)
    assert request.window_hours == int(days) * 24 and request.research_mode is ResearchMode.DETAILED
    assert request.categories == (Category.CYBER,)
    assert request.research_source_ids == tuple(
        f"research_publisher_{key}" for key in CYBER_BRIEFING_PUBLISHER_IDS
    )
    assert set(CYBER_BRIEFING_PUBLISHER_IDS) < set(CYBER_PUBLISHER_IDS)
    assert "cyber_cert_ua" in CYBER_PUBLISHER_IDS
    assert "exact supplied reporting range" in request.question
    assert "Nation-state activity" in request.question and "GNSS" in request.question
    assert (
        "unverified claim" in request.question and "not when exploitation began" in request.question
    )
    assert "never total attacks" in request.question
    assert len(request.question) <= 2_000


@pytest.mark.parametrize("days", CyberWindowDays)
@pytest.mark.parametrize("status", ["completed", "failed", "paused", "needs_review"])
def test_daily_markers_protect_each_window_and_status_across_midnight(days, status):
    record = job(status=status)
    record = replace(
        record, request_key=cyber_briefing_key(record.owner_id, NOW - timedelta(days=1), days)
    )
    assert retains_daily_admission(record, NOW + timedelta(hours=23))
    assert not retains_daily_admission(record, NOW + timedelta(hours=24))


def test_identity_isolates_owner_window_and_other_briefing_families():
    owner = uuid4()
    values = {cyber_briefing_key(owner, NOW, days) for days in CyberWindowDays}
    assert len(values) == 5
    assert cyber_briefing_key(uuid4(), NOW, CyberWindowDays.TWO) not in values
    assert economy_briefing_key(owner, NOW) not in values


@pytest.mark.parametrize("days", CyberWindowDays)
async def test_api_freezes_requested_period_and_reuses_personal_job_without_model_calls(
    client, user, container, days
):
    gateway, headers = await prepared(container, client)
    now = container.clock.now()
    response = await client.post(f"/api/cyber/briefing?days={int(days)}", headers=headers)
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["window_days"] == int(days)
    assert datetime.fromisoformat(payload["period_from"]) == now - timedelta(days=days)
    assert datetime.fromisoformat(payload["period_to"]) == now
    assert datetime.fromisoformat(payload["next_refresh_at"]) == now + timedelta(hours=24)
    frozen = (await stored(container, payload["job"]["id"])).payload["input"]
    assert frozen["scope"]["window_hours"] == int(days) * 24
    assert frozen["scope"]["categories"] == ["cyber"]
    container.clock.advance(timedelta(minutes=10))
    repeated = await client.post(f"/api/cyber/briefing?days={int(days)}", headers=headers)
    assert repeated.status_code == 202, repeated.text
    assert repeated.json()["job"]["id"] == payload["job"]["id"]
    assert repeated.json()["period_to"] == payload["period_to"]
    assert not gateway.calls


async def test_each_window_has_its_own_durable_job_and_get_never_starts_work(
    client, user, container
):
    gateway, headers = await prepared(container, client)
    assert (await client.get("/api/cyber/briefing", headers=headers)).status_code == 405
    responses = []
    for days in CyberWindowDays:
        response = await client.post(f"/api/cyber/briefing?days={int(days)}", headers=headers)
        assert response.status_code == 202, response.text
        responses.append(response)
        job_id = response.json()["job"]["id"]
        assert (
            await client.post(f"/api/report-jobs/{job_id}/pause", headers=headers)
        ).status_code == 200
        # Retained daily markers cannot be discarded to start the same paid work again.
        assert (
            await client.delete(f"/api/report-jobs/{job_id}", headers=headers)
        ).status_code == 422
    assert len({response.json()["job"]["id"] for response in responses}) == 5
    assert not gateway.calls


def test_selected_publishers_fit_research_plan_and_retention_without_expanding_caps(container):
    request = cyber_briefing_request()
    query = ResearchQuery(
        question=request.question,
        since=NOW - timedelta(days=2),
        until=NOW,
        terms=request.research_terms,
        source_ids=request.research_source_ids,
        mode=ResearchMode.DETAILED,
    )
    plan = container.research.plan(query)
    assert {row.source_id for row in plan.tasks if row.selected} == set(request.research_source_ids)
    assert all(row.supported for row in plan.tasks if row.selected)
    budget = budget_for(Category.CYBER)
    assert budget.window >= timedelta(days=max(CyberWindowDays)) and budget.max_items == 8_000


async def test_worker_collects_cyber_only_and_preserves_cited_retained_observations(
    client, user, container, monkeypatch
):
    gateway, headers = await prepared(container, client)
    now = container.clock.now()
    retained = make_event(
        "kev",
        source_id="cisa_kev",
        category=Category.CYBER,
        subtype="known_exploited_vulnerability",
        title="CVE exploitation advisory",
        published_at=now - timedelta(days=1),
        observed_at=now,
    )
    container.store.upsert((retained,))
    source = "research_publisher_cyber_acsc_advisories"
    collect = AsyncMock(
        return_value=ResearchBatch(
            items=(
                make_event(
                    "publisher",
                    source_id=source,
                    category=Category.CYBER,
                    subtype="advisory",
                    title="Security vulnerability advisory",
                    published_at=now - timedelta(hours=2),
                    observed_at=now,
                    point=None,
                ),
            )
        )
    )
    monkeypatch.setattr(container.research, "collect", collect)
    # Durable research jobs acquire sources through the checkpointed path.
    monkeypatch.setattr(container.research, "collect_checkpointed", collect)
    response = await client.post("/api/cyber/briefing?days=14", headers=headers)
    assert response.status_code == 202, response.text
    await work(container)
    current = await stored(container, response.json()["job"]["id"])
    assert current.status in {"completed", "needs_review"}, (current.status, current.error)
    async with container.session_factory() as session:
        version = await container.repositories(session).reports.get_version(current.report_id, 1)
    assert {item.source_id for item in version.evidence} == {"cisa_kev", source}
    assert version.body.cited_labels() <= {item.label for item in version.evidence}
    assert collect.call_args.args[0].since == now - timedelta(days=14)
    assert collect.call_args.args[0].until == now
    assert collect.call_args.args[0].source_ids == cyber_briefing_request().research_source_ids
    assert gateway.calls

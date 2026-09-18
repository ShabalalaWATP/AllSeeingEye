"""Queued report reranking respects daily allowances without charging text twice."""

from datetime import timedelta
from uuid import UUID

import pytest

from ai_usage_helpers import add_policy, policy, reservations
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.domain.ai_usage import AiAllowancePeriod, AiPolicyScope
from ase.domain.report_search import EmbeddingResult
from feeds_helpers import make_event
from llm_fixture_helpers import seed_legacy_profile
from report_job_api_helpers import job_settings, prepared, stored, submit, work
from team_helpers import CONTEXT

__all__ = ["job_settings"]


class RecordingEmbeddings:
    def __init__(self):
        self.calls = []

    async def embed(self, base_url, api_key, model, texts):
        self.calls.append((base_url, api_key, model, tuple(texts)))
        return EmbeddingResult(tuple((1.0, 0.0) for _ in texts), 1, 34)


async def configure_embeddings(container):
    embeddings = RecordingEmbeddings()
    container.embedding_gateway = embeddings
    profile = await seed_legacy_profile(
        container,
        {
            "name": "Queued embedding profile",
            "base_url": "https://embeddings.test/v1",
            "model": "frozen-embedding-model",
            "api_key": "synthetic-embedding-key",
            "roles": ["embeddings"],
            "max_output_tokens": 64,
            "temperature": 0.0,
        },
    )
    return embeddings, profile


@pytest.mark.parametrize("team_scope", [False, True])
@pytest.mark.parametrize("request_limit", [0, 11])
async def test_queued_embeddings_use_daily_allowance_and_exact_actor_scope(
    client, user, container, team_scope, request_limit
):
    text_gateway, headers = await prepared(container, client)
    embeddings, embedding_profile = await configure_embeddings(container)
    team_id = None
    if team_scope:
        team = await client.post("/api/teams", headers=headers, json={"name": "Report desk"})
        assert team.status_code == 201, team.text
        team_id = UUID(team.json()["id"])
    current_policy = policy(
        limit=request_limit,
        tokens=None,
        scope=AiPolicyScope.TEAM if team_scope else AiPolicyScope.USER,
        target_id=team_id if team_scope else user.id,
        period=AiAllowancePeriod.DAY,
    )
    await add_policy(container, current_policy)
    report = {"template": "intsum", "team_id": str(team_id) if team_id else None}
    queued = await submit(client, headers, report=report)
    await work(container)
    final = await stored(container, queued.json()["id"])
    rows = await reservations(container)
    if request_limit == 0:
        assert embeddings.calls == []
        assert text_gateway.calls == []
        assert rows == []
        assert final.status == "paused"
        return
    assert final.status == "needs_review", (final.status, final.error)
    assert len(embeddings.calls) == 1
    assert embeddings.calls[0][:3] == (
        embedding_profile.base_url,
        "synthetic-embedding-key",
        embedding_profile.model,
    )
    assert len(text_gateway.calls) == 10
    assert [name for name, _ in text_gateway.calls if name.startswith("synthesis_")] == [
        "synthesis_judgements",
        "synthesis_alternatives",
        "synthesis_collection",
    ]
    # Ten already-metered text calls plus exactly one embedding reservation.
    assert len(rows) == 11
    assert all(row.user_id == user.id and row.team_id == team_id for row in rows)
    assert all(row.policy_id == current_policy.id for row in rows)
    [embedding_row] = [row for row in rows if row.purpose == "report:evidence_rerank"]
    assert embedding_row.profile_id == embedding_profile.id
    assert embedding_row.model == embedding_profile.model
    assert embedding_row.prompt_tokens == embedding_row.actual_tokens == 34
    assert embedding_row.completion_tokens == 0
    assert embedding_row.ok is True
    async with container.session_factory() as session:
        totals = await container.repositories(session).ai_usage.account_totals(
            user.id, container.clock.now()
        )
        assert totals.used_requests == 11
        assert totals.used_tokens == 34 + 10 * 15


async def test_subscription_reranking_is_charged_to_owner_once(client, user, container):
    text_gateway, _headers = await prepared(container, client)
    embeddings, embedding_profile = await configure_embeddings(container)
    await add_policy(
        container,
        policy(
            limit=11,
            tokens=None,
            scope=AiPolicyScope.USER,
            target_id=user.id,
            period=AiAllowancePeriod.DAY,
        ),
    )
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            user, ScheduleInput(name="Daily observation", template_id="intsum"), CONTEXT
        )
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    container.store.upsert(
        tuple(
            make_event(
                str(index),
                source_id="usgs_earthquakes",
                title=f"Instrument observation {index}",
                published_at=container.clock.now() - timedelta(minutes=2),
                observed_at=container.clock.now() - timedelta(minutes=2),
            )
            for index in range(4)
        )
    )
    assert await container.schedule_runner.run_once() == 1
    await work(container)
    async with container.session_factory() as session:
        [edition] = await SqlSubscriptionEditionRepository(session).history(schedule.id)
    final = await stored(container, edition.job_id)
    assert final.status == "needs_review", (final.status, final.error)
    assert len(embeddings.calls) == 1 and len(text_gateway.calls) == 10
    rows = await reservations(container)
    assert len(rows) == 11
    assert all(row.user_id == user.id and row.team_id is None and not row.system for row in rows)
    [embedding_row] = [row for row in rows if row.purpose == "report:evidence_rerank"]
    assert embedding_row.profile_id == embedding_profile.id
    assert embedding_row.actual_tokens == 34

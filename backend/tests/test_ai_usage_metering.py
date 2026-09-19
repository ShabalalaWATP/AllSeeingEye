"""Newly metered model paths are attributed to the right account, team or system budget."""

from __future__ import annotations

import json
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_usage_helpers import NOW, add_policy, policy, reservations
from ase.adapters.persistence.teams import TeamMembershipRow, TeamRow
from ase.application import ai_usage_gateway
from ase.application.assistant.report_context import ReportContextReader
from ase.domain.ai_usage import AiAllowanceExceeded, AiPolicyScope
from ase.domain.assistant import AssistantQuestion, AssistantReportSelection
from ase.domain.llm import LlmMessage, LlmRequest, LlmResult
from assistant_helpers import Gateway, nothing
from assistant_helpers import profile as eye_profile
from feeds_helpers import make_event
from helpers import USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_documents_helpers import document_records
from report_helpers import PROFILE, ScriptedGateway
from report_search_helpers import FakeEmbeddings, add_profile, add_report
from team_helpers import CONTEXT
from test_claim_repository import seed
from test_generate_claims import output_for, setup_model


async def _totals(container, *, user_id=None, team_id=None, system=False):
    async with container.session_factory() as session:
        repo = container.repositories(session).ai_usage
        now = container.clock.now()
        if system:
            return await repo.system_totals(now)
        if team_id is not None:
            return await repo.team_totals(team_id, now)
        return await repo.account_totals(user_id, now)


async def test_ask_eye_report_question_on_team_edition_charges_the_team(container, user):
    team_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            TeamRow(
                id=team_id,
                name="Desk",
                is_active=True,
                created_by=user.id,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        # PostgreSQL enforces the membership foreign key, so the team must exist first.
        await session.flush()
        session.add(
            TeamMembershipRow(team_id=team_id, user_id=user.id, role="member", joined_at=NOW)
        )
        record, version = document_records(user.id)
        record.team_id = team_id
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    await add_policy(
        container, policy(limit=5, tokens=None, scope=AiPolicyScope.TEAM, target_id=team_id)
    )
    await eye_profile(container)
    gateway = Gateway()
    gateway.content = json.dumps(
        {"paragraphs": [{"kind": "finding", "text": "Fighting is assessed.", "citations": ["E1"]}]}
    )
    container.llm = gateway
    question = AssistantQuestion(
        "El Fasher fighting", scope="report", report=AssistantReportSelection(record.id, 1)
    )
    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.report_reader = ReportContextReader(container.get_report(session))
        await service.execute(user, question, check_session=nothing)
    [row] = await reservations(container)
    assert row.team_id == team_id and row.user_id == user.id
    assert (await _totals(container, team_id=team_id)).used_requests == 1


async def test_manual_claim_generation_is_charged_to_the_requesting_account(
    client, container, user, monkeypatch
):
    await setup_model(container, user)
    report, version, _ = await seed(container, user)
    await add_policy(container, policy(limit=None, tokens=None))
    gateway = AsyncMock()
    gateway.complete.return_value = LlmResult(output_for(version), "returned", 5, 10, 20)
    monkeypatch.setattr(container, "llm", gateway)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        "/api/claims/generate",
        headers=headers,
        json={"report_id": str(report.id), "version_number": 1},
    )
    assert response.status_code == 200, response.text
    [row] = await reservations(container)
    assert row.purpose == "claims:claim_proposals" and row.user_id == user.id
    totals = await _totals(container, user_id=user.id)
    assert (totals.used_requests, totals.used_tokens) == (1, 30)


async def test_semantic_search_embeddings_are_charged_and_refused_when_blocked(container, user):
    embeddings = FakeEmbeddings()
    container.embedding_gateway = embeddings
    async with container.session_factory() as session:
        await add_profile(container, session)
        await add_report(container, session, user)
    async with container.session_factory() as session:
        await container.report_search(session).index(user)
    totals = await _totals(container, user_id=user.id)
    assert (totals.used_requests, totals.used_tokens) == (1, 30)
    await add_policy(
        container, policy(limit=0, tokens=None, scope=AiPolicyScope.USER, target_id=user.id)
    )
    async with container.session_factory() as session:
        with pytest.raises(AiAllowanceExceeded):
            await container.report_search(session).query(user, "maritime")
    assert len(embeddings.calls) == 1


async def test_admin_connection_test_is_charged_to_the_administrator(container, admin):
    profile = await seed_legacy_profile(container, PROFILE)
    container.llm = ScriptedGateway('{"ok": true}')
    async with container.session_factory() as session:
        outcome = await container.test_llm_profile(session).execute(admin, profile.id, CONTEXT)
    assert outcome.ok
    totals = await _totals(container, user_id=admin.id)
    assert (totals.used_requests, totals.used_tokens) == (1, 70)


async def test_feed_translation_uses_the_system_budget(container, admin):
    container.llm = gateway = ScriptedGateway(
        '{"translations":["Talks resume"]}', '{"translations":["Talks resume"]}'
    )
    await seed_legacy_profile(container, {**PROFILE, "roles": ["translation"]})
    queue = container.build_translation_queue()
    event = replace(
        make_event("foreign", title="Les pourparlers reprennent", published_at=NOW),
        language="fr",
    )
    blocked = policy(limit=0, tokens=None, scope=AiPolicyScope.SYSTEM)
    await add_policy(container, blocked)
    container.store.upsert([event])
    assert await queue.run_once() == 0
    assert gateway.requests == []  # Refused before dispatch; retried on a later cycle.
    async with container.session_factory() as session:
        repo = container.repositories(session).ai_usage
        current = await repo.get_policy(blocked.id)
        assert current is not None
        await repo.save_policy(replace(current, request_limit=None, revision=2))
        await session.commit()
    assert await queue.run_once() == 1
    [row] = await reservations(container)
    assert row.system and row.user_id is None
    totals = await _totals(container, system=True)
    assert (totals.used_requests, totals.used_tokens) == (1, 70)


def test_large_prompts_reserve_the_full_conservative_input_bound() -> None:
    request = LlmRequest(
        (
            LlmMessage("system", "s" * 80_000),
            LlmMessage("user", "u" * 80_000),
        ),
        4_000,
        0.0,
    )
    assert ai_usage_gateway._request_tokens(request) == 164_000

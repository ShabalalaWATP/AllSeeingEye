"""Real report, schedule and shared-service wiring honours destination assignments."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.dto import RequestContext
from ase.application.model_routing import ModelRouting
from ase.application.ports.feeds import EventQuery
from ase.application.reports.request import ReportRequest
from ase.application.schedules.report_request import scheduled_report_request
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmConnectionBinding, LlmResult, LlmRole, ReasoningEffort
from ase.domain.schedules import Schedule
from ase.domain.teams import MembershipRole
from report_helpers import filled_store, good_body
from team_helpers import CONTEXT, team_service
from test_direction_advocacy import ADVOCACY, DIRECTION
from test_model_routing import profile


async def save_binding(container, actor, value, team_id=None):
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.llm_bindings.save(
            LlmConnectionBinding(
                team_id,
                value.id,
                value.revision,
                value.config_hash,
                container.clock.now(),
                actor.id,
            )
        )
        await session.commit()


async def setup_routing(container, admin, user):
    async with team_service(container) as service:
        first = await service.create(admin, "Routing team A", CONTEXT)
        second = await service.create(admin, "Routing team B", CONTEXT)
        for team in (first, second):
            await service.set_member(
                admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
    values = [
        profile(name, reasoning_effort=effort)
        for name, effort in (
            ("global-model", ReasoningEffort.LOW),
            ("team-model", ReasoningEffort.HIGH),
        )
    ]
    async with container.session_factory() as session:
        for value in values:
            value.api_key_encrypted = container.cipher.encrypt("fixture-" + value.model)
            value.tested_config_hash = value.config_hash
            await container.repositories(session).llm_profiles.add(value)
        await session.commit()
    await save_binding(container, admin, values[0])
    await save_binding(container, admin, values[1], first.id)
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    return first, second, values


class Gateway:
    def __init__(self, on_first=None):
        self.calls = []
        self.on_first = on_first

    async def complete(self, base_url, api_key, model, request):
        self.calls.append((model, api_key, request.reasoning_effort, request.schema_name))
        if len(self.calls) == 1 and self.on_first:
            await self.on_first()
        content = {
            "direction": DIRECTION,
            "report": good_body(),
            "advocacy": ADVOCACY,
            # The post-draft stages route like every other call, so they answer plainly.
            "report_analysis": {
                "sections": [
                    {
                        "heading": "What this means",
                        "text": "The reporting establishes movement and suggests intent.",
                        "evidence": ["E1"],
                    }
                ],
                "diagram": None,
            },
            "entailment": {"assessments": []},
            "contradiction_analysis": {"disagreements": []},
        }
        if request.schema_name == "claim_proposals":
            item = json.loads(request.messages[1].content)["evidence"][0]
            content["claim_proposals"] = {
                "claims": [
                    {
                        "statement": "The source reports this observation.",
                        "kind": "reported_fact",
                        "citations": [
                            {
                                "label": item["label"],
                                "relation": "supporting",
                                "field": "title",
                                "text": item["title"],
                            }
                        ],
                        "unresolved_conflicts": [],
                    }
                ]
            }
        return LlmResult(json.dumps(content[request.schema_name]), model, 1, 5, 10)


@pytest.mark.parametrize("destination", ["team_a", "team_b", "personal", "admin"])
async def test_create_routes_all_text_calls_by_destination_not_actor_memberships(
    container, admin, user, destination
):
    first, second, values = await setup_routing(container, admin, user)
    team_id = {"team_a": first.id, "team_b": second.id}.get(destination)
    expected = values[1] if destination == "team_a" else values[0]
    container.llm = gateway = Gateway()
    request = ReportRequest(
        "ask",
        question="Will fighting increase?",
        team_id=team_id,
        profile_id=values[0].id if team_id == first.id else values[1].id,
        devils_advocacy=True,
    )
    async with container.session_factory() as session:
        record, version = await container.generate_report(session).execute(
            admin if destination == "admin" else user, request, RequestContext()
        )
    assert {call[3] for call in gateway.calls} == {
        "direction",
        "report",
        "advocacy",
        "report_analysis",
        "entailment",
        "claim_proposals",
    }
    assert {(call[0], call[1], call[2]) for call in gateway.calls} == {
        (expected.model, "fixture-" + expected.model, expected.reasoning_effort)
    }
    assert version.model_routing.destination_team_id == team_id
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 1)
    assert saved.model_routing == version.model_routing
    assert saved.claim_generation.model_origin.requested_model == expected.model


async def test_mid_run_rebinding_changes_next_regeneration_only(container, admin, user):
    first, _, values = await setup_routing(container, admin, user)

    async def switch():
        await save_binding(container, admin, values[0], first.id)

    container.llm = original = Gateway(switch)
    request = ReportRequest(
        "ask", question="Will fighting increase?", team_id=first.id, devils_advocacy=True
    )
    async with container.session_factory() as session:
        record, first_version = await container.generate_report(session).execute(
            user, request, RequestContext()
        )
    assert {call[0] for call in original.calls} == {values[1].model}
    container.llm = subsequent = Gateway()
    async with container.session_factory() as session:
        _, second_version = await container.generate_report(session).regenerate(
            user, record.id, RequestContext()
        )
        historical = await container.repositories(session).reports.get_version(record.id, 1)
    assert {call[0] for call in subsequent.calls} == {values[0].model}
    assert historical.model_routing == first_version.model_routing
    assert second_version.model_routing != first_version.model_routing
    assert historical.claim_generation == first_version.claim_generation
    assert first_version.claim_generation.model_origin.requested_model == values[1].model
    assert second_version.claim_generation.model_origin.requested_model == values[0].model


async def test_schedule_uses_its_own_team_and_shared_translation_uses_global(
    container, admin, user
):
    first, _, values = await setup_routing(container, admin, user)
    container.llm = gateway = Gateway()
    now = container.clock.now()
    schedule = Schedule(
        uuid4(),
        "Team morning",
        "intsum",
        None,
        None,
        6,
        "daily",
        0,
        None,
        True,
        user.id,
        now,
        now,
        team_id=first.id,
    )
    async with container.session_factory() as session:
        record, _ = await container.generate_report(session).execute(
            user, scheduled_report_request(schedule), RequestContext()
        )
    assert {call[0] for call in gateway.calls} == {values[1].model}
    assert record.team_id == first.id
    assert (await container._translation_profile()).id == values[0].id


async def test_disabled_binding_stops_before_outbound_calls(container, admin, user):
    first, _, values = await setup_routing(container, admin, user)
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.save(replace(values[1], enabled=False))
        await session.commit()
    container.llm = gateway = Gateway()
    async with container.session_factory() as session:
        with pytest.raises(NoModelAvailable):
            await container.generate_report(session).execute(
                user, ReportRequest("intsum", team_id=first.id), RequestContext()
            )
    assert not gateway.calls
    assert (await container._translation_profile()).id == values[0].id


async def test_shared_embeddings_exclude_team_only_profile(container, admin, user):
    _first, _, values = await setup_routing(container, admin, user)

    async with container.session_factory() as session:
        repos = container.repositories(session)
        # Deliberate direct-state fixture: text binding cannot turn a team's key into
        # the credential for indexing every visible personal/team report.
        values[1].roles |= {LlmRole.EMBEDDINGS}
        await repos.llm_profiles.save(values[1])
        embedding = profile("embeddings", roles=frozenset({LlmRole.EMBEDDINGS}))
        await repos.llm_profiles.add(embedding)
        await session.commit()
        assert (
            await ModelRouting(repos.llm_profiles, repos.llm_bindings).embeddings()
        ).id == embedding.id

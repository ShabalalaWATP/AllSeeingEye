"""Detailed report production traverses the actual native adapter and HTTP contract."""

import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import httpx

from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.router import RoutingLlmGateway
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production import Producer
from ase.domain.llm import TEXT_ROLES, LlmProvider
from ase.domain.reports import MAX_JUDGEMENT_CHARS
from ase.domain.research import ResearchBatch, ResearchMode
from feeds_helpers import make_event
from planning_integration_helpers import synthetic_plan
from post_draft_stage_helpers import POST_DRAFT_STAGES
from production_integration_helpers import RecordingUsage, production_job
from report_helpers import filled_store, good_body
from test_report_challenge import plans, reviews


async def test_native_bedrock_runs_direction_local_repair_challenge_redraft_and_review(
    container, user
):
    original = production_job(user, container.cipher)
    profile = replace(
        original.profile,
        provider=LlmProvider.BEDROCK,
        roles=TEXT_ROLES,
        base_url="https://bedrock-runtime.eu-west-2.amazonaws.com",
        model="amazon.nova-pro-v1:0",
        reasoning_effort=None,
    )
    job = replace(
        original,
        profile=profile,
        now=original.now + timedelta(hours=1),
        request=replace(original.request, research_mode=ResearchMode.DETAILED),
    )
    invalid = good_body(
        key_judgements=[
            {
                **good_body()["key_judgements"][0],
                "statement": "x" * (MAX_JUDGEMENT_CHARS + 1),
            }
        ]
    )
    responses = {
        "direction": [
            {"pir": "What changed?", "sirs": [], "eeis": [], "search_terms": [], "categories": []}
        ],
        "research_plan": [{"candidates": [], "tasks": []}],
        "report": [invalid, good_body(), good_body()],
        "challenge_plan": [plans()],
        "challenge_reviews": [reviews()],
        "report_analysis": [POST_DRAFT_STAGES["report_analysis"]],
        "entailment": [{"assessments": []}],
    }
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == profile.base_url + "/model/amazon.nova-pro-v1%3A0/converse"
        assert request.headers["authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        requests.append(payload)
        assert "Private" not in request.url.path
        specification = payload["outputConfig"]["textFormat"]["structure"]["jsonSchema"]
        schema = specification["schema"]
        assert '"maxLength"' not in schema and '"maxItems"' not in schema
        return httpx.Response(
            200,
            json={
                "stopReason": "end_turn",
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [{"text": json.dumps(responses[specification["name"]].pop(0))}],
                    }
                },
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
            },
        )

    collection = AsyncMock()
    collection.plan = synthetic_plan
    collection.collect.return_value = ResearchBatch()
    event = make_event(
        title="New contrary observation",
        source_id="new-source",
        observed_at=job.now,
        published_at=job.now - timedelta(minutes=1),
    )
    collection.challenge_many.return_value = (ResearchBatch(items=(event,)), ResearchBatch())
    usage = RecordingUsage()
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as native,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as compatible,
    ):
        gateway = RoutingLlmGateway(
            OpenAiCompatibleGateway(client=compatible), BedrockConverseGateway(client=native)
        )
        producer = Producer(
            store=filled_store(),
            source_profiles={},
            cipher=container.cipher,
            gateway=gateway,
            usage=usage,
            research=collection,
            private_store_factory=InMemoryEventStore,
        )
        version = await producer.produce(job, AsyncMock(return_value=profile))
    stages = [
        payload["outputConfig"]["textFormat"]["structure"]["jsonSchema"]["name"]
        for payload in requests
    ]
    assert stages == [
        "direction",
        "research_plan",
        "report",
        "report",
        "challenge_plan",
        "report",
        "challenge_reviews",
        "report_analysis",
        "entailment",
    ]
    assert all(not answers for answers in responses.values())
    assert version.challenge.redrafted
    assert len(version.challenge.reviews) == len(version.body.key_judgements) == 2
    assert all(len(row.statement) <= MAX_JUDGEMENT_CHARS for row in version.body.key_judgements)
    assert "schema" in json.dumps(requests[3]["messages"]).lower()
    assert version.prompt_tokens == 90 and version.completion_tokens == 45
    assert version.model == profile.model

"""Every text stage retains the selected native provider, including repair and challenge."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.llm.translator import LlmTranslator
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production import Producer
from ase.domain.llm import TEXT_ROLES, LlmProvider
from ase.domain.research import ResearchBatch, ResearchMode
from feeds_helpers import make_event
from planning_integration_helpers import SchemaGateway, synthetic_plan
from production_integration_helpers import RecordingUsage, production_job
from report_helpers import ScriptedGateway, filled_store, good_body
from test_direction_advocacy import ADVOCACY
from test_report_challenge import plans, reviews


@pytest.mark.parametrize("detailed", [False, True])
async def test_bedrock_provider_survives_every_report_stage_and_redraft(container, user, detailed):
    original = production_job(user, container.cipher)
    profile = replace(
        original.profile,
        provider=LlmProvider.BEDROCK,
        base_url="https://bedrock-runtime.eu-west-2.amazonaws.com",
        model="amazon.nova-pro-v1:0",
        roles=TEXT_ROLES,
        reasoning_effort=None,
    )
    job = replace(
        original,
        profile=profile,
        now=original.now + timedelta(hours=1),
        request=replace(
            original.request, research_mode=ResearchMode.DETAILED if detailed else None
        ),
    )
    responses = {"direction": [{"pir": "What changed?", "search_terms": []}]}
    if detailed:
        responses.update(
            {
                "research_plan": [{"candidates": [], "tasks": []}],
                "report": [good_body(), good_body()],
                "challenge_plan": [plans()],
                "challenge_reviews": [reviews()],
            }
        )
        expected = [
            "direction",
            "research_plan",
            "report",
            "challenge_plan",
            "report",
            "challenge_reviews",
        ]
    else:
        responses.update({"report": [{}, good_body()], "advocacy": [ADVOCACY]})
        expected = ["direction", "report", "report", "advocacy"]
    gateway = SchemaGateway(responses)
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
    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=gateway,
        usage=RecordingUsage(),
        research=collection,
        private_store_factory=InMemoryEventStore,
    )
    version = await producer.produce(job, AsyncMock(return_value=profile))
    assert [request.schema_name for request in gateway.requests] == expected
    assert all(request.provider is LlmProvider.BEDROCK for request in gateway.requests)
    assert all(request.reasoning_effort is None for request in gateway.requests)
    if detailed:
        assert version.challenge.redrafted
        assert len(version.challenge.reviews) == len(version.body.key_judgements) == 2
    else:
        assert version.advocacy is not None
        assert version.attempts == 2


async def test_live_translation_retains_native_provider(container, user):
    profile = replace(production_job(user, container.cipher).profile, provider=LlmProvider.BEDROCK)
    gateway = ScriptedGateway('{"translations":["English title"]}')
    translator = LlmTranslator(
        AsyncMock(return_value=profile), AsyncMock(), container.cipher, gateway, container.clock
    )
    assert await translator.translate([("Titre français", "fr")]) == ["English title"]
    assert gateway.requests[0].provider is LlmProvider.BEDROCK

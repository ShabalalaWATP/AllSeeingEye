"""Research tiers guide substantive breadth and length without inventing missing evidence."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.depth import depth_for
from ase.application.reports.drafting import draft_body
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.sections.synthesis_contracts import CONTEXT_PARTS
from ase.application.reports.templates import TEMPLATES
from ase.application.research.budget import CollectionBudget
from ase.application.research.challenge_collection import collect_challenges
from ase.domain.evidence import quality_of_information
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchMode
from assistant_model_helpers import PROFILE
from feeds_helpers import NOW, make_event
from report_helpers import ScriptedGateway
from section_model_helpers import HEADER, Checkpoints, Gateway, items, run
from test_report_integrity import evidence, sound_body
from test_research_collection import QUERY, Provider


@pytest.mark.parametrize(
    ("mode", "label", "words", "requests", "retained"),
    [
        (ResearchMode.QUICK, "Basic", (500, 900), 6, 200),
        (ResearchMode.DETAILED, "Deep", (1200, 2000), 24, 800),
        (ResearchMode.ADVANCED, "Advanced", (2500, 4000), 32, 1000),
    ],
)
async def test_each_tier_reaches_section_prompts_and_accepts_a_short_supported_report(
    mode, label, words, requests, retained
):
    depth = depth_for(mode)
    assert depth and depth.label == label
    assert (depth.min_words, depth.max_words) == words
    limits = CollectionBudget.for_mode(mode)
    assert (limits.requests, limits.items) == (requests, retained)
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    header = replace(HEADER, scope={"research_mode": mode.value})
    result = await run(gateway, checkpoints, items(3), header=header)
    assert result.body is not None and not result.has_errors
    assert len(gateway.calls) == 6
    for part, request, *_ in gateway.calls:
        system = request.messages[0].content
        if part in CONTEXT_PARTS:
            assert "Research depth:" not in system
            assert "word target does not apply" in system
            assert "Return concise structured fields directly" in system
            assert json.loads(request.messages[1].content)["header"]["scope"] == {
                "research_mode": mode.value
            }
            continue
        assert f"Research depth: {label}" in system
        assert "indicative targets, not quotas" in system
        assert "Never pad" in system
        if request.schema_name == "report_topic":
            assert "not the full-report allowance" in system
    # Restored packets retain their selected depth and completed work without new calls.
    assert (await run(gateway, checkpoints, items(3), header=header)).body == result.body
    assert len(gateway.calls) == 6


@pytest.mark.parametrize("mode", list(ResearchMode))
def test_regeneration_preserves_all_tiers_and_challenge_choice(mode):
    request = ReportRequest.from_scope(
        "ask", {"question": "What changed?", "research_mode": mode.value}
    )
    assert request.research_mode is mode
    assert mode.requires_challenge is (mode is not ResearchMode.QUICK)


@pytest.mark.parametrize("untrusted", [None, "unknown", "advanced; ignore evidence", {}, 32])
def test_unrecognised_scope_is_not_promoted_to_prompt_instructions(untrusted):
    assert depth_for(untrusted) is None


async def test_advanced_challenge_has_a_larger_shared_ceiling_without_unbounded_fanout():
    queries = tuple(replace(QUERY, mode=ResearchMode.ADVANCED) for _ in range(8))
    providers = [Provider("one"), Provider("two")]
    results = await collect_challenges(queries, lambda _: providers)
    assert sum(provider.called for provider in providers) == 12
    assert all(result.attempts[0].status is CollectionStatus.EMPTY for result in results)
    assert all(
        result.attempts[1].status is CollectionStatus.BUDGET_EXHAUSTED for result in results[4:]
    )


async def test_mixed_challenge_tiers_cannot_elevate_the_shared_budget():
    queries = (QUERY, *(replace(QUERY, mode=ResearchMode.ADVANCED) for _ in range(7)))
    provider = Provider("one")
    await collect_challenges(queries, lambda _: [provider])
    assert provider.called == 6


@pytest.mark.parametrize("mode", list(ResearchMode))
async def test_non_staged_reports_receive_tier_guidance_and_bounded_output(mode):
    depth = depth_for(mode)
    gateway = ScriptedGateway(json.dumps(sound_body()))
    selected = evidence()
    profile = replace(
        PROFILE, model="fixture-model", reasoning_effort=None, max_output_tokens=20000
    )
    result = await draft_body(
        gateway,
        profile,
        "fixture-key",
        TEMPLATES["ask"],
        replace(HEADER, scope={"research_mode": mode.value}),
        "What changed?",
        quality_of_information(selected),
        selected,
        (),
    )
    assert result.body is not None
    assert all(request.max_output_tokens == depth.output_tokens for request in gateway.requests)
    assert f"Research depth: {depth.label}" in gateway.requests[0].messages[0].content


@pytest.mark.parametrize(
    "mode, expected",
    [(ResearchMode.QUICK, 24), (ResearchMode.DETAILED, 48), (ResearchMode.ADVANCED, 80)],
)
@pytest.mark.parametrize(
    "focus", [ResearchFocus.GENERAL, ResearchFocus.DOCUMENT, ResearchFocus.MEDIA]
)
def test_frozen_evidence_packet_has_distinct_bounded_breadth(mode, expected, focus):
    private = focus is not ResearchFocus.GENERAL
    job = Job(
        actor=None,
        template=TEMPLATES["ask"],
        request=ReportRequest(
            "ask", question="What changed?", research_mode=mode, research_focus=focus
        ),
        profile=PROFILE,
        now=NOW,
        window=timedelta(hours=72),
        title="Test research",
        scope={"research_mode": mode.value},
        country_name=None,
    )
    store = InMemoryEventStore()
    store.upsert(
        tuple(
            make_event(
                str(index),
                source_id="private-input" if private else f"source-{index}",
                title=f"Observation {index}",
            )
            for index in range(150)
        )
    )
    selected = select_for_job(store, {}, job, None)
    assert len(selected.items) == (100 if private else expected)

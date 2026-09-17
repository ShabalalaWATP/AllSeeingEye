"""Successful step reuse, safe pauses and smaller attempts after explicit exhaustion."""

import asyncio
import json
from dataclasses import replace

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.reports.sections import SectionIncomplete
from ase.application.reports.sections.checkpoints import metadata, write_state
from ase.application.reports.sections.planning import (
    LEGACY_METHOD_VERSION,
    PREVIOUS_METHOD_VERSION,
    packet_digest,
    plan_topics,
)
from ase.application.reports.sections.synthesis_contracts import (
    ALTERNATIVES,
    COLLECTION,
    JUDGEMENTS,
)
from ase.application.reports.templates import TEMPLATES
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.llm import LlmProvider, ReasoningEffort
from assistant_model_helpers import PROFILE
from section_model_helpers import (
    HEADER,
    Checkpoints,
    Gateway,
    exhausted,
    items,
    run,
    synthesis_part_body,
    topic_body,
)


async def test_assembly_keeps_topic_text_citations_and_can_resume_without_any_calls():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    first = await run(gateway, checkpoints)
    assert first.body and not first.has_errors and first.attempts == 6
    assert first.prompt_tokens == 60 and first.completion_tokens == 30
    assert [theme.items[0].text for theme in first.body.reporting] == [
        f"Original reporting from E{x}." for x in range(1, 4)
    ]
    assert first.body.cited_labels() == {"E1", "E2", "E3"}
    assert all(row.status == "completed" for row in checkpoints.rows.values())
    assert all("test-key-marker" not in repr(row) for row in checkpoints.rows.values())
    resumed = await run(gateway, checkpoints)
    assert resumed.body == first.body and len(gateway.calls) == 6 and resumed.attempts == 0
    assert resumed.prompt_tokens is None and resumed.completion_tokens is None


async def test_one_item_packet_preserves_supported_requirement_without_a_false_gap():
    selected = (replace(items(1)[0], title="Nuclear inspection completed"),)
    direction = Direction("What changed?", eeis=("Which nuclear inspection was completed?",))
    checkpoints = Checkpoints()

    draft = await run(Gateway(checkpoints), checkpoints, selected, direction=direction)

    assert draft.body and draft.supported_requirements == {"EEI-1"}
    assert not any(gap.eei == "EEI-1" for gap in draft.body.gaps)


@pytest.mark.parametrize("method_version", [PREVIOUS_METHOD_VERSION, LEGACY_METHOD_VERSION])
async def test_legacy_directional_resume_uses_body_inference_without_false_gaps(method_version):
    original = items()
    selected = (replace(original[0], title="Nuclear inspection completed"), *original[1:])
    direction = Direction("What changed?", eeis=("Which nuclear inspection was completed?",))
    quality = quality_of_information(selected)
    question = "What does the supplied evidence establish?"
    topics = plan_topics(selected, direction, method_version=method_version)
    digest = packet_digest(
        PROFILE,
        TEMPLATES["ask"],
        HEADER,
        question,
        quality,
        selected,
        (),
        direction,
        None,
        method_version=method_version,
    )
    checkpoints = Checkpoints()
    first = topics[0]
    await write_state(
        checkpoints,
        digest,
        metadata(first, first.evidence_labels),
        "completed",
        body=topic_body(first.evidence_labels),
    )

    draft = await run(Gateway(checkpoints), checkpoints, selected, direction=direction)

    assert draft.body and draft.supported_requirements is None
    assert not any(gap.eei == "EEI-1" for gap in draft.body.gaps)


async def test_topic_exhaustion_splits_once_and_accounts_failed_paid_attempt():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {"S1": exhausted()})
    draft = await run(gateway, checkpoints, items(8))
    names = [name for name, *_ in gateway.calls]
    assert names[:3] == ["S1", "S1.1", "S1.2"] and names.count("S1") == 1
    assert draft.body and not draft.has_errors
    assert draft.attempts == 9 and draft.prompt_tokens == 100 and draft.completion_tokens == 32040
    split = next(row for (_, key), row in checkpoints.rows.items() if key == "S1")
    assert split.status == "split" and split.payload["children"] == ["S1.1", "S1.2"]
    before = len(gateway.calls)
    assert (await run(gateway, checkpoints, items(8))).body == draft.body
    assert len(gateway.calls) == before


async def test_unsplittable_topic_keeps_finished_sections_and_is_not_replayed_on_resume():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {"S2": exhausted()})
    for _ in range(2):
        with pytest.raises(SectionIncomplete) as caught:
            await run(gateway, checkpoints)
        assert caught.value.section_id == "S2" and caught.value.reason == "token_budget_exhausted"
    assert [name for name, *_ in gateway.calls] == ["S1", "S2"]
    assert any(
        key == "S1" and row.status == "completed" for (_, key), row in checkpoints.rows.items()
    )


async def test_exhausted_synthesis_never_repeats_all_topic_work_or_same_synthesis():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {COLLECTION: exhausted(completion_tokens=16000)})
    for _ in range(2):
        with pytest.raises(SectionIncomplete) as caught:
            await run(gateway, checkpoints)
        assert caught.value.section_id == COLLECTION
    assert [name for name, *_ in gateway.calls] == [
        "S1",
        "S2",
        "S3",
        JUDGEMENTS,
        ALTERNATIVES,
        COLLECTION,
    ]
    assert sum(row.status == "completed" for row in checkpoints.rows.values()) == 5


async def test_one_failed_step_can_be_repaired_on_explicit_resume_without_rewriting_others():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {"S2": LlmGatewayError("private-provider-marker")})
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints)
    assert "private-provider-marker" not in str(caught.value) + repr(checkpoints.rows)
    gateway.overrides.clear()
    draft = await run(gateway, checkpoints)
    assert draft.body and not draft.has_errors
    assert [name for name, *_ in gateway.calls] == [
        "S1",
        "S2",
        "S2",
        "S3",
        JUDGEMENTS,
        ALTERNATIVES,
        COLLECTION,
    ]
    assert "previous step" in gateway.calls[2][1].messages[-1].content


async def test_invalid_final_assumptions_pause_synthesis_and_reuse_completed_topics():
    checkpoints = Checkpoints()
    invalid = synthesis_part_body(JUDGEMENTS, ["E1"])
    invalid["key_judgements"][0]["assumptions"] = ["A999"]
    gateway = Gateway(checkpoints, {JUDGEMENTS: json.dumps(invalid)})
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints)
    assert caught.value.reason == "invalid_section" and caught.value.draft.has_errors
    gateway.overrides.clear()
    assert (await run(gateway, checkpoints)).body
    assert [name for name, *_ in gateway.calls].count("S1") == 1
    assert [name for name, *_ in gateway.calls].count(JUDGEMENTS) == 2


async def test_changed_frozen_metadata_invalidates_reuse_even_with_same_ids_and_hash():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    await run(gateway, checkpoints)
    updated = tuple(replace(row, source_name="Revised attribution") for row in items())
    await run(gateway, checkpoints, updated)
    assert len(gateway.calls) == 12 and len({digest for digest, _ in checkpoints.rows}) == 2


async def test_cancelled_running_step_is_not_replayed_or_saved_as_completed():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {"S1": asyncio.CancelledError()})
    with pytest.raises(asyncio.CancelledError):
        await run(gateway, checkpoints)
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints)
    assert caught.value.reason == "interrupted" and len(gateway.calls) == 1
    assert next(iter(checkpoints.rows.values())).status == "running"


async def test_split_depth_and_twelve_leaf_cap_bound_failure_recursion():
    checkpoints = Checkpoints()
    topics = plan_topics(items(100), None)
    overrides = {topic.id: exhausted() for topic in topics}
    overrides.update({f"{topic.id}.{index}": exhausted() for topic in topics for index in (1, 2)})
    gateway = Gateway(checkpoints, overrides)
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints, items(100))
    assert caught.value.reason == "token_budget_exhausted"
    assert len(checkpoints.rows) <= 25 and len(gateway.calls) <= 25
    assert all(name.count(".") <= 2 for name, *_ in gateway.calls)


@pytest.mark.parametrize("provider", [LlmProvider.OPENAI_COMPATIBLE, LlmProvider.BEDROCK])
async def test_every_call_preserves_selected_provider_and_effort_budget(provider):
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    profile = replace(
        PROFILE, provider=provider, reasoning_effort=ReasoningEffort.MAX, max_output_tokens=32000
    )
    await run(gateway, checkpoints, items(1), profile=profile)
    assert len(gateway.calls) == 4
    for name, request, base, key, model in gateway.calls:
        assert (base, key, model) == (profile.base_url, "test-key-marker", profile.model)
        assert request.provider is provider and request.reasoning_effort is ReasoningEffort.MAX
        assert request.max_output_tokens == (16000 if name in (ALTERNATIVES, COLLECTION) else 32000)

"""Small final steps resume historical topic packets without another omnibus request."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.ports.section_checkpoints import SectionCheckpoint
from ase.application.reports.sections import SectionIncomplete
from ase.application.reports.sections.checkpoints import metadata
from ase.application.reports.sections.planning import (
    LEGACY_METHOD_VERSION,
    PREVIOUS_METHOD_VERSION,
    packet_digest,
    plan_topics,
)
from ase.application.reports.sections.synthesis_contracts import (
    CONTEXT,
    CONTEXT_SCHEMA,
    JUDGEMENTS,
    JUDGEMENTS_SCHEMA,
    validate_part,
)
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence import quality_of_information
from assistant_model_helpers import PROFILE
from section_model_helpers import (
    HEADER,
    Checkpoints,
    Gateway,
    exhausted,
    items,
    run,
    synthesis_body,
    synthesis_part_body,
    topic_body,
)
from test_model_schema_contracts import assert_strict_objects


def old_packet(checkpoints, *, status="incomplete", reason="provider_error"):
    evidence = items(4)
    digest = packet_digest(
        PROFILE,
        TEMPLATES["ask"],
        HEADER,
        "What does the supplied evidence establish?",
        quality_of_information(evidence),
        evidence,
        (),
        None,
        None,
    )
    for topic in plan_topics(evidence, None):
        checkpoints.rows[digest, topic.id] = SectionCheckpoint(
            "completed",
            {**metadata(topic, topic.evidence_labels), "body": topic_body(topic.evidence_labels)},
        )
    payload = metadata(None, tuple(row.label for row in evidence))
    if status == "completed":
        payload["body"] = synthesis_body(["E1"])
    checkpoints.rows[digest, "synthesis"] = SectionCheckpoint(status, payload, reason)
    return evidence, digest


@pytest.mark.parametrize("schema", [JUDGEMENTS_SCHEMA, CONTEXT_SCHEMA])
def test_new_subset_wire_contracts_are_strict_and_keep_original_evidence_pattern(schema):
    assert_strict_objects(schema)
    assert "^E[1-9][0-9]*$" in json.dumps(schema)
    assert not {"reporting", "assessment"} & schema["properties"].keys()


async def test_old_four_completed_topics_keep_digest_and_only_new_final_parts_run():
    checkpoints = Checkpoints()
    evidence, digest = old_packet(checkpoints)
    topics = {key: deepcopy(row) for key, row in checkpoints.rows.items() if key[1] != "synthesis"}
    gateway = Gateway(checkpoints)
    draft = await run(gateway, checkpoints, evidence)
    assert draft.body and not draft.has_errors
    assert [name for name, *_ in gateway.calls] == [JUDGEMENTS, CONTEXT]
    assert {key[0] for key in checkpoints.rows} == {digest}
    assert all(checkpoints.rows[key] == row for key, row in topics.items())
    for part in (JUDGEMENTS, CONTEXT):
        row = checkpoints.rows[digest, part]
        assert row.status == "completed" and row.payload["parent"] == "synthesis"
    assert checkpoints.rows[digest, "synthesis"].status == "completed"


@pytest.mark.parametrize("method_version", [LEGACY_METHOD_VERSION, PREVIOUS_METHOD_VERSION])
async def test_prior_packet_digest_and_topics_resume_without_replanning_or_rewriting(
    method_version,
):
    checkpoints = Checkpoints()
    evidence = items(4)
    digest = packet_digest(
        PROFILE,
        TEMPLATES["ask"],
        HEADER,
        "What does the supplied evidence establish?",
        quality_of_information(evidence),
        evidence,
        (),
        None,
        None,
        method_version=method_version,
    )
    for topic in plan_topics(evidence, None, method_version=method_version):
        checkpoints.rows[digest, topic.id] = SectionCheckpoint(
            "completed",
            {**metadata(topic, topic.evidence_labels), "body": topic_body(topic.evidence_labels)},
        )
    checkpoints.rows[digest, "synthesis"] = SectionCheckpoint(
        "incomplete",
        metadata(None, tuple(row.label for row in evidence)),
        "provider_error",
    )

    gateway = Gateway(checkpoints)
    draft = await run(gateway, checkpoints, evidence)

    assert draft.body and not draft.has_errors
    assert [name for name, *_ in gateway.calls] == [JUDGEMENTS, CONTEXT]
    assert {key[0] for key in checkpoints.rows} == {digest}


async def test_existing_completed_omnibus_is_reused_without_calls_or_child_replacement():
    checkpoints = Checkpoints()
    evidence, digest = old_packet(checkpoints, status="completed", reason=None)
    gateway = Gateway(checkpoints)
    before = deepcopy(checkpoints.rows)
    assert (await run(gateway, checkpoints, evidence)).body
    assert not gateway.calls and checkpoints.rows == before
    assert (digest, JUDGEMENTS) not in checkpoints.rows


async def test_old_running_omnibus_needs_explicit_resume_reset_before_new_substeps():
    checkpoints = Checkpoints()
    evidence, digest = old_packet(checkpoints, status="running", reason=None)
    gateway = Gateway(checkpoints)
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints, evidence)
    assert caught.value.reason == "interrupted" and not gateway.calls
    parent = checkpoints.rows[digest, "synthesis"]
    assert parent.status == "running"
    checkpoints.rows[digest, "synthesis"] = replace(
        parent, status="incomplete", reason="interrupted"
    )
    assert (await run(gateway, checkpoints, evidence)).body
    assert [name for name, *_ in gateway.calls] == [JUDGEMENTS, CONTEXT]


async def test_context_failure_resume_reuses_saved_judgements_and_does_not_repeat_topics():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {CONTEXT: LlmGatewayError("private-error-marker")})
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints)
    assert caught.value.section_id == CONTEXT and caught.value.reason == "provider_error"
    saved = next(deepcopy(row) for (_, key), row in checkpoints.rows.items() if key == JUDGEMENTS)
    gateway.overrides.clear()
    assert (await run(gateway, checkpoints)).body
    names = [name for name, *_ in gateway.calls]
    assert names == ["S1", "S2", "S3", JUDGEMENTS, CONTEXT, CONTEXT]
    assert next(row for (_, key), row in checkpoints.rows.items() if key == JUDGEMENTS) == saved
    packet = json.loads(gateway.calls[-1][1].messages[1].content)
    assert packet["validated_judgements_not_evidence"] == saved.payload["body"]
    assert len(packet["original_frozen_evidence"]) == 3
    assert "private-error-marker" not in repr(checkpoints.rows)


async def test_changed_saved_judgement_cannot_be_reused_or_overwritten():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {CONTEXT: LlmGatewayError("unavailable")})
    with pytest.raises(SectionIncomplete):
        await run(gateway, checkpoints)
    key = next(key for key in checkpoints.rows if key[1] == JUDGEMENTS)
    original = checkpoints.rows[key]
    payload = deepcopy(original.payload)
    payload["body"]["key_judgements"][0]["supporting_evidence"] = ["E999"]
    checkpoints.rows[key] = replace(original, payload=payload)
    before = len(gateway.calls)
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints)
    assert caught.value.reason == "invalid_checkpoint" and len(gateway.calls) == before
    assert checkpoints.rows[key].status == "completed" and checkpoints.rows[key].payload == payload


def test_judgement_subset_requires_prior_version_change_before_reuse():
    value = synthesis_part_body(JUDGEMENTS, ["E1"])
    value["key_judgements"][0]["change_from_previous"] = None
    with pytest.raises(ValueError):
        validate_part(
            value, part=JUDGEMENTS, labels=frozenset({"E1"}), eeis=frozenset(), previous_exists=True
        )


@pytest.mark.parametrize("part", [JUDGEMENTS, CONTEXT])
async def test_exhausted_child_is_never_replayed_with_identical_allowance(part):
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {part: exhausted()})
    for _ in range(2):
        with pytest.raises(SectionIncomplete) as caught:
            await run(gateway, checkpoints)
        assert caught.value.section_id == part and caught.value.reason == "token_budget_exhausted"
    assert [name for name, *_ in gateway.calls].count(part) == 1
    assert [name for name, *_ in gateway.calls].count("S1") == 1


@pytest.mark.parametrize("part", [JUDGEMENTS, CONTEXT])
@pytest.mark.parametrize("mutation", ["citation", "html", "extra", "duplicate_ids"])
def test_part_boundary_rejects_untrusted_or_unlinked_output_before_checkpointing(part, mutation):
    value = synthesis_part_body(part, ["E1"])
    if mutation == "citation":
        if part == JUDGEMENTS:
            value["key_judgements"][0]["supporting_evidence"] = ["E999"]
        else:
            value["alternative_hypotheses"] = [
                {"text": "Other", "why_less_likely": "Sparse", "evidence": ["E999"]}
            ]
    elif mutation == "html":
        if part == JUDGEMENTS:
            value["key_judgements"][0]["confidence_statement"] = "<script>bad</script>"
        else:
            value["sourcing_statement"] = "<script>bad</script>"
    elif mutation == "extra":
        value["reporting"] = []
    elif part == JUDGEMENTS:
        value["key_judgements"].append(deepcopy(value["key_judgements"][0]))
    else:
        value["alternative_hypotheses"] = [
            {"text": "Other", "why_less_likely": "Sparse", "evidence": ["E1", "E1"]}
        ]
    with pytest.raises(ValueError):
        validate_part(value, part=part, labels=frozenset({"E1"}), eeis=frozenset())

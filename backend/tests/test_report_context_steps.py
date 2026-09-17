"""Final context splits once, preserving paid and completed synthesis checkpoints."""

from copy import deepcopy
from dataclasses import replace

import pytest

from ase.application.ports.section_checkpoints import SectionCheckpoint
from ase.application.reports.drafting import Draft
from ase.application.reports.sections.checkpoints import metadata, synthesis_metadata, write_state
from ase.application.reports.sections.outcomes import SectionIncomplete, StepExhausted
from ase.application.reports.sections.synthesis import collect_synthesis
from ase.application.reports.sections.synthesis_contracts import (
    CONTEXT,
    JUDGEMENTS,
    PARTS,
    schema_for,
    validate_part,
)
from section_model_helpers import Checkpoints, synthesis_body
from test_model_schema_contracts import assert_strict_objects

DIGEST = "a" * 64
LABELS = ("E1",)
ALTERNATIVES = "synthesis_alternatives"
COLLECTION = "synthesis_collection"
CHILDREN = (ALTERNATIVES, COLLECTION)
FIELDS = {
    JUDGEMENTS: ("key_judgements", "assumptions"),
    ALTERNATIVES: ("alternative_hypotheses", "indicators_and_warning"),
    COLLECTION: ("gaps", "collection_recommendations", "sourcing_statement"),
}
FIELDS[CONTEXT] = (*FIELDS[ALTERNATIVES], *FIELDS[COLLECTION])


def body_for(part):
    body = synthesis_body(LABELS)
    return {key: body[key] for key in FIELDS[part]}


def child_metadata(part):
    if part in PARTS:
        return synthesis_metadata(part, LABELS)
    return {
        **metadata(None, LABELS),
        "id": part,
        "title": "Alternatives and warning" if part == ALTERNATIVES else "Gaps and collection",
        "parent": CONTEXT,
    }


def saved(checkpoints, part, status="completed", reason=None):
    payload = child_metadata(part)
    if status == "completed":
        payload["body"] = body_for(part)
    elif status == "split":
        payload["children"] = list(CHILDREN)
    checkpoints.rows[DIGEST, part] = SectionCheckpoint(status, payload, reason)


async def collect(checkpoints, calls, failures=None):
    draft = Draft()
    failures = failures or {}

    async def pause(expected, reason):
        await write_state(checkpoints, DIGEST, expected, "incomplete", reason=reason)
        raise SectionIncomplete(expected["id"], reason, draft)

    async def call(expected, *, part, repair, judgements):
        calls.append((part, repair, deepcopy(judgements)))
        await write_state(checkpoints, DIGEST, expected, "running")
        if failures.get(part) == "exhausted":
            await write_state(
                checkpoints, DIGEST, expected, "incomplete", reason="token_budget_exhausted"
            )
            raise StepExhausted
        if failures.get(part) == "invalid":
            await pause(expected, "invalid_section")
        return body_for(part)

    return await collect_synthesis(
        checkpoints,
        DIGEST,
        metadata(None, LABELS),
        frozenset(),
        draft,
        call=call,
        pause=pause,
        previous_exists=False,
    )


async def test_new_context_uses_two_durable_children_and_preserves_legacy_parent_identity():
    checkpoints, calls = Checkpoints(), []
    result = await collect(checkpoints, calls)
    assert [part for part, *_ in calls] == [JUDGEMENTS, *CHILDREN]
    assert result == synthesis_body(LABELS)
    assert checkpoints.rows[DIGEST, "synthesis"].payload == {
        **metadata(None, LABELS),
        "children": list(PARTS),
    }
    context = checkpoints.rows[DIGEST, CONTEXT]
    assert context.status == "completed"
    assert context.payload == {**synthesis_metadata(CONTEXT, LABELS), "body": body_for(CONTEXT)}
    for part in CHILDREN:
        child = checkpoints.rows[DIGEST, part]
        assert child.status == "completed" and child.payload["parent"] == CONTEXT
    assert all(judgements == body_for(JUDGEMENTS) for _, _, judgements in calls[1:])


async def test_completed_legacy_context_and_judgements_are_not_replayed_or_rewritten():
    checkpoints, calls = Checkpoints(), []
    for part in PARTS:
        saved(checkpoints, part)
    before = deepcopy(checkpoints.rows)
    assert await collect(checkpoints, calls) == synthesis_body(LABELS)
    assert not calls
    assert all(checkpoints.rows[key] == row for key, row in before.items())
    assert not any(part in CHILDREN for _, part in checkpoints.rows)


async def test_exhausted_legacy_context_splits_without_replaying_accepted_judgements():
    checkpoints, calls = Checkpoints(), []
    saved(checkpoints, JUDGEMENTS)
    saved(checkpoints, CONTEXT, "incomplete", "token_budget_exhausted")
    judgement = deepcopy(checkpoints.rows[DIGEST, JUDGEMENTS])
    assert await collect(checkpoints, calls) == synthesis_body(LABELS)
    assert [part for part, *_ in calls] == list(CHILDREN)
    assert checkpoints.rows[DIGEST, JUDGEMENTS] == judgement
    assert all(not repair for _, repair, _ in calls)


async def test_partial_context_resume_keeps_accepted_child_and_original_failure_reason():
    checkpoints, calls = Checkpoints(), []
    saved(checkpoints, JUDGEMENTS)
    with pytest.raises(SectionIncomplete) as caught:
        await collect(checkpoints, calls, {COLLECTION: "invalid"})
    assert (caught.value.section_id, caught.value.reason) == (COLLECTION, "invalid_section")
    accepted = deepcopy(checkpoints.rows[DIGEST, ALTERNATIVES])
    assert checkpoints.rows[DIGEST, CONTEXT].status == "split"
    assert await collect(checkpoints, calls) == synthesis_body(LABELS)
    assert [part for part, *_ in calls] == [ALTERNATIVES, COLLECTION, COLLECTION]
    assert calls[-1][1] is True
    assert checkpoints.rows[DIGEST, ALTERNATIVES] == accepted


@pytest.mark.parametrize("part", (CONTEXT, *CHILDREN))
async def test_running_context_or_child_requires_explicit_resume_before_any_call(part):
    checkpoints, calls = Checkpoints(), []
    saved(checkpoints, JUDGEMENTS)
    if part in CHILDREN:
        saved(checkpoints, CONTEXT, "split")
    if part == COLLECTION:
        saved(checkpoints, ALTERNATIVES)
    saved(checkpoints, part, "running")
    before = deepcopy(checkpoints.rows[DIGEST, part])
    with pytest.raises(SectionIncomplete) as caught:
        await collect(checkpoints, calls)
    assert (caught.value.section_id, caught.value.reason) == (part, "interrupted")
    assert not calls and checkpoints.rows[DIGEST, part] == before


@pytest.mark.parametrize("part", CHILDREN)
async def test_child_exhaustion_is_terminal_and_never_subdivides_or_replays(part):
    checkpoints, calls = Checkpoints(), []
    saved(checkpoints, JUDGEMENTS)
    for _ in range(2):
        with pytest.raises(SectionIncomplete) as caught:
            await collect(checkpoints, calls, {part: "exhausted"})
        assert (caught.value.section_id, caught.value.reason) == (part, "token_budget_exhausted")
    assert [name for name, *_ in calls].count(part) == 1
    assert CONTEXT not in [name for name, *_ in calls]
    assert checkpoints.rows[DIGEST, part].status == "incomplete"


async def test_changed_split_children_cannot_dispatch_a_different_context_plan():
    checkpoints, calls = Checkpoints(), []
    saved(checkpoints, JUDGEMENTS)
    saved(checkpoints, CONTEXT, "split")
    row = checkpoints.rows[DIGEST, CONTEXT]
    checkpoints.rows[DIGEST, CONTEXT] = replace(
        row, payload={**row.payload, "children": list(reversed(CHILDREN))}
    )
    with pytest.raises(SectionIncomplete) as caught:
        await collect(checkpoints, calls)
    assert caught.value.reason == "invalid_checkpoint" and not calls


async def test_corrupt_completed_child_is_neither_overwritten_nor_replayed():
    checkpoints, calls = Checkpoints(), []
    saved(checkpoints, JUDGEMENTS)
    saved(checkpoints, CONTEXT, "split")
    saved(checkpoints, ALTERNATIVES)
    row = checkpoints.rows[DIGEST, ALTERNATIVES]
    changed = replace(row, payload={**row.payload, "parent": "synthesis"})
    checkpoints.rows[DIGEST, ALTERNATIVES] = changed
    with pytest.raises(SectionIncomplete) as caught:
        await collect(checkpoints, calls)
    assert caught.value.reason == "invalid_checkpoint" and not calls
    assert checkpoints.rows[DIGEST, ALTERNATIVES] == changed


@pytest.mark.parametrize("part", CHILDREN)
def test_child_schema_is_strict_and_accepts_only_its_bounded_fields(part):
    schema = schema_for(part, remaining_gaps=2, research_mode="quick")
    assert_strict_objects(schema)
    assert set(schema["properties"]) == set(FIELDS[part])
    if part == COLLECTION:
        assert schema["properties"]["gaps"]["maxItems"] == 2
    value = body_for(part)
    assert validate_part(value, part=part, labels=frozenset(LABELS), eeis=frozenset()) == value
    value["key_judgements"] = []
    with pytest.raises(ValueError):
        validate_part(value, part=part, labels=frozenset(LABELS), eeis=frozenset())

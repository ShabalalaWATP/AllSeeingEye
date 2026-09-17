"""Final assessment limits follow the saved research tier, not a universal cap."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from ase.application.reports.sections import SectionIncomplete
from ase.application.reports.sections.synthesis_contracts import (
    ALTERNATIVES,
    CONTEXT,
    JUDGEMENTS,
    schema_for,
    validate_part,
)
from ase.domain.research import ResearchMode
from section_model_helpers import HEADER, Checkpoints, Gateway, items, run, synthesis_part_body


@pytest.mark.parametrize(
    ("mode", "judgements", "alternatives"),
    [
        (ResearchMode.QUICK, 3, 2),
        (ResearchMode.DETAILED, 5, 3),
        (ResearchMode.ADVANCED, 8, 4),
    ],
)
@pytest.mark.parametrize("context_part", [CONTEXT, ALTERNATIVES])
def test_each_tier_has_strict_model_schema_and_validates_its_own_ceiling(
    mode, judgements, alternatives, context_part
):
    judgement_schema = schema_for(JUDGEMENTS, research_mode=mode.value)
    context_schema = schema_for(context_part, research_mode=mode.value)
    assert judgement_schema["properties"]["key_judgements"]["maxItems"] == judgements
    assert context_schema["properties"]["alternative_hypotheses"]["maxItems"] == alternatives

    judgement = synthesis_part_body(JUDGEMENTS, ["E1"])
    base = judgement["key_judgements"][0]
    judgement["key_judgements"] = [
        {**deepcopy(base), "id": f"KJ{number}"} for number in range(1, judgements + 1)
    ]
    assert (
        len(
            validate_part(
                judgement,
                part=JUDGEMENTS,
                labels=frozenset({"E1"}),
                eeis=frozenset(),
                research_mode=mode.value,
            )["key_judgements"]
        )
        == judgements
    )
    with pytest.raises(ValueError):
        validate_part(
            {**judgement, "key_judgements": [*judgement["key_judgements"], deepcopy(base)]},
            part=JUDGEMENTS,
            labels=frozenset({"E1"}),
            eeis=frozenset(),
            research_mode=mode.value,
        )

    context = synthesis_part_body(context_part, ["E1"])
    context["alternative_hypotheses"] = [
        {
            "text": f"Alternative {number}.",
            "why_less_likely": "Limited support.",
            "evidence": ["E1"],
        }
        for number in range(alternatives)
    ]
    assert (
        len(
            validate_part(
                context,
                part=context_part,
                labels=frozenset({"E1"}),
                eeis=frozenset(),
                research_mode=mode.value,
            )["alternative_hypotheses"]
        )
        == alternatives
    )
    with pytest.raises(ValueError):
        validate_part(
            {
                **context,
                "alternative_hypotheses": [
                    *context["alternative_hypotheses"],
                    context["alternative_hypotheses"][0],
                ],
            },
            part=context_part,
            labels=frozenset({"E1"}),
            eeis=frozenset(),
            research_mode=mode.value,
        )


async def test_advanced_runner_accepts_three_distinct_judgements_and_preserves_resume():
    checkpoints = Checkpoints()
    judgement = synthesis_part_body(JUDGEMENTS, ["E1"])
    base = judgement["key_judgements"][0]
    judgement["key_judgements"] = [
        {**deepcopy(base), "id": f"KJ{number}"} for number in range(1, 4)
    ]
    context = synthesis_part_body(ALTERNATIVES, ["E1"])
    context["alternative_hypotheses"] = [
        {
            "text": "An alternative explanation.",
            "why_less_likely": "Its source basis is thin.",
            "evidence": ["E1"],
        }
    ]
    gateway = Gateway(
        checkpoints, {JUDGEMENTS: json.dumps(judgement), ALTERNATIVES: json.dumps(context)}
    )
    header = replace(HEADER, scope={"research_mode": ResearchMode.ADVANCED.value})
    draft = await run(gateway, checkpoints, items(3), header=header)
    assert draft.body and len(draft.body.key_judgements) == 3
    request = next(request for name, request, *_ in gateway.calls if name == JUDGEMENTS)
    assert request.json_schema["properties"]["key_judgements"]["maxItems"] == 8
    assert "ceiling is not a target" in request.messages[0].content
    assert len(draft.body.alternative_hypotheses) == 1
    count = len(gateway.calls)
    resumed = await run(gateway, checkpoints, items(3), header=header)
    assert resumed.body == draft.body and len(gateway.calls) == count


async def test_basic_runner_rejects_four_judgements_before_checkpointing():
    checkpoints = Checkpoints()
    judgement = synthesis_part_body(JUDGEMENTS, ["E1"])
    base = judgement["key_judgements"][0]
    judgement["key_judgements"] = [
        {**deepcopy(base), "id": f"KJ{number}"} for number in range(1, 5)
    ]
    gateway = Gateway(checkpoints, {JUDGEMENTS: json.dumps(judgement)})
    header = replace(HEADER, scope={"research_mode": ResearchMode.QUICK.value})
    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints, header=header)
    assert caught.value.section_id == JUDGEMENTS
    assert caught.value.reason == "invalid_section"
    assert not any(
        section_id == JUDGEMENTS and row.status == "completed"
        for (_, section_id), row in checkpoints.rows.items()
    )

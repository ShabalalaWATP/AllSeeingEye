"""Unsupported EEIs belong in gaps, not forced paragraphs with unrelated citations."""

from copy import deepcopy

import pytest

from ase.application.reports.prompts import compose_messages
from ase.application.reports.templates import TEMPLATES
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.report_input import parse_model_body
from ase.domain.validation import validate_body
from feeds_helpers import NOW
from test_report_integrity import evidence, sound_body

DIRECTION = Direction(
    pir="What does the supplied assessment establish?",
    eeis=(
        "What claim was reported?",
        "Which supplied observations support it?",
        "Is original metadata available?",
        "Has a reverse-image search established the source?",
        "Is there a matching independently dated photograph?",
        "Has the location been independently verified?",
        "Has image authenticity been established?",
        "Which further checks are needed?",
    ),
)


def test_direction_retains_every_question_without_demanding_unsupported_assessments():
    messages = compose_messages(
        TEMPLATES["ask"],
        scope_line="Supplied assessment",
        period_from=NOW,
        period_to=NOW,
        question=DIRECTION.pir,
        quality=quality_of_information(evidence()),
        evidence=evidence(),
        direction=DIRECTION,
    )
    user = messages[1].content
    for index, question in enumerate(DIRECTION.eeis, 1):
        assert f"EEI-{index}: {question}" in user
    assert "one assessment section per EEI" not in user
    assert "Put unsupported EEIs in gaps" in user
    assert "Group related supported EEIs" in user
    assert "does not establish that a check was performed" in user
    assert "Never invent evidence" in messages[0].content


def compact_body():
    data = deepcopy(sound_body())
    data["assessment"][0]["heading"] = "EEI-1 and EEI-2: supplied reporting"
    data["gaps"] = [
        {"eei": f"EEI-{index}", "text": f"The packet does not establish: {question}"}
        for index, question in enumerate(DIRECTION.eeis, 1)
        if index > 2
    ]
    return data


def test_grouped_supported_assessment_and_named_gaps_fit_existing_strict_validation():
    body = parse_model_body(compact_body())
    result = validate_body(body, frozenset(), {}, evidence_items=evidence())
    assert result.passed
    assert len(result.body.assessment) == 1
    assert [gap.eei for gap in result.body.gaps] == [f"EEI-{index}" for index in range(3, 9)]
    assert result.body.cited_labels() <= {"E1", "E2", "E3"}


@pytest.mark.parametrize("citation", [[], ["E999"]])
def test_grouped_assessment_still_requires_known_evidence(citation):
    data = compact_body()
    data["assessment"][0]["evidence"] = citation
    if not citation:
        with pytest.raises(ValueError):
            parse_model_body(data)
    else:
        result = validate_body(parse_model_body(data), frozenset(), {}, evidence_items=evidence())
        assert not result.passed
        assert any(finding.rule == "citation" for finding in result.errors)

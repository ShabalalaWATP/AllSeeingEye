"""Generation must not present unsupported or malformed analysis as validated."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.reports.drafting import draft_body
from ase.application.reports.templates import TEMPLATES
from ase.domain.doctrine import Confidence
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.report_input import parse_model_body
from ase.domain.report_records import (
    body_from_dict,
    body_to_dict,
    quality_from_dict,
    quality_to_dict,
)
from ase.domain.reports import ReportBody, ReportHeader, ReportParseError, parse_body
from ase.domain.validation import validate_body
from feeds_helpers import NOW, make_event
from report_helpers import GOOD_BODY, ScriptedGateway


def sound_body() -> dict:
    data = deepcopy(GOOD_BODY)
    data.pop("unexpected", None)
    data["key_judgements"][1]["contradicting_evidence"] = []
    return data


def evidence() -> tuple[EvidenceItem, ...]:
    base = EvidenceItem.from_event(
        "E1", make_event("a"), NOW, source_name="One", independence_key="one"
    )
    return (
        replace(base, grade="C3", reliability="C", credibility=3),
        replace(base, label="E2", event_id="b", independence_key="two", grade="A2", credibility=2),
        replace(
            base, label="E3", event_id="c", independence_key="three", grade="A2", credibility=2
        ),
    )


def checked(data: dict):
    return validate_body(parse_body(data), frozenset({"E1", "E2", "E3"}), {})


def test_empty_report_cannot_pass_but_failed_record_remains_constructible() -> None:
    assert ReportBody() == parse_body({})
    assert not checked({}).passed


def test_unknown_evidence_and_assumptions_cannot_pass() -> None:
    data = sound_body()
    data["key_judgements"][0]["supporting_evidence"] = ["E999"]
    data["key_judgements"][0]["assumptions"] = ["A999"]
    result = checked(data)
    assert {"citation", "assumption", "evidence"} <= {f.rule for f in result.errors}


def test_known_assumption_is_not_a_substitute_for_observed_support() -> None:
    data = sound_body()
    data["key_judgements"][0]["supporting_evidence"] = []
    assert "evidence" in {f.rule for f in checked(data).errors}


@pytest.mark.parametrize("field", ["key_judgements", "assumptions"])
def test_duplicate_identifiers_are_rejected(field: str) -> None:
    data = sound_body()
    data[field].append(deepcopy(data[field][0]))
    assert "identifier" in {f.rule for f in checked(data).errors}


def test_two_same_probability_terms_do_not_make_one_judgement() -> None:
    data = sound_body()
    data["key_judgements"][0]["statement"] = (
        "We assess it is highly likely that fighting grows and highly likely that talks fail."
    )
    assert "yardstick" in {f.rule for f in checked(data).errors}


def test_unrelated_strong_evidence_cannot_lift_weak_judgement() -> None:
    data = sound_body()
    data["key_judgements"][0]["supporting_evidence"] = ["E1"]
    data["key_judgements"][0]["confidence"] = "high"
    result = validate_body(
        parse_body(data), frozenset({"E1", "E2", "E3"}), {}, evidence_items=evidence()
    )
    assert result.body.key_judgements[0].confidence is Confidence.LOW
    assert "low" in result.body.key_judgements[0].confidence_statement.lower()


def test_reporting_grade_is_derived_from_each_cited_frozen_item() -> None:
    data = sound_body()
    data["reporting"][0]["items"][0].update(evidence=["E1", "E2"], grade="A1")
    result = validate_body(
        parse_body(data), frozenset({"E1", "E2", "E3"}), {}, evidence_items=evidence()
    )
    assert result.body.reporting[0].items[0].grade == "C3, A2"
    assert "grade" in {f.rule for f in result.findings}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.clear(),
        lambda data: data.update(assessment=[]),
        lambda data: data.update(sourcing_statement="   "),
        lambda data: data["assumptions"][0].update(lynchpin="false"),
        lambda data: data["key_judgements"][0].update(statement="x" * 401),
        lambda data: data["key_judgements"][0].update(supporting_evidence=["E1"] * 21),
        lambda data: data["key_judgements"][0].pop("confidence_statement"),
        lambda data: data.update(unknown="silently discarded"),
        lambda data: data["key_judgements"][0].update(probability="certain"),
    ],
)
def test_new_model_boundary_rejects_missing_blank_coerced_and_truncated_fields(mutate) -> None:
    data = sound_body()
    mutate(data)
    with pytest.raises(ReportParseError):
        parse_model_body(data)


def test_new_model_boundary_accepts_sound_schema() -> None:
    assert parse_model_body(sound_body()).assessment


def test_generated_grades_survive_persistence_without_truncation() -> None:
    data = sound_body()
    data["reporting"][0]["items"][0]["evidence"] = ["E1", "E2"]
    result = validate_body(parse_body(data), frozenset(), {}, evidence_items=evidence())
    stored = json.loads(json.dumps(body_to_dict(result.body)))
    assert body_from_dict(stored).reporting[0].items[0].grade == "C3, A2"


def test_contradictions_are_unassessed_and_null_in_serialised_quality() -> None:
    quality = quality_of_information(evidence())
    payload = quality_to_dict(quality)
    assert payload["contradictions"] is None
    assert quality_from_dict(payload) == quality
    legacy = quality_from_dict({**payload, "contradictions": 0})
    assert legacy.contradictions == 0
    assert "contradictions not automatically assessed" in legacy.describe()


def test_sourcing_counts_only_cited_evidence_and_marks_model_rationale() -> None:
    data = sound_body()
    data["key_judgements"] = [data["key_judgements"][0]]
    data["key_judgements"][0].update(supporting_evidence=["E1"], confidence="low")
    data["reporting"][0]["items"] = [data["reporting"][0]["items"][0]]
    data["alternative_hypotheses"] = []
    data["sourcing_statement"] = "A hundred verified independent sources confirm this."
    result = validate_body(parse_body(data), frozenset(), {}, evidence_items=evidence())
    assert result.passed
    assert "1 evidence items" in result.body.sourcing_statement
    assert "hundred" not in result.body.sourcing_statement
    assert "independently verified" in result.body.sourcing_statement
    statement = result.body.key_judgements[0].confidence_statement
    assert "Cited support: 1 item(s)" in statement
    assert "Model rationale (unverified):" in statement
    stored = body_from_dict(json.loads(json.dumps(body_to_dict(result.body))))
    assert stored == result.body


def test_declared_groups_and_multiple_copies_do_not_create_high_confidence() -> None:
    item = evidence()[1]
    copies = [replace(item, label=f"E{i}", independence_key=f"publisher{i}") for i in range(4)]
    quality = quality_of_information(copies)
    assert quality.independent_organisations == 1
    assert quality.confidence_ceiling is Confidence.MODERATE
    assert "independent sourcing not verified" in quality.describe()


def test_high_ceiling_requires_confirmed_distinct_support_and_no_contradictions() -> None:
    items = (
        replace(
            evidence()[0],
            credibility=1,
            grade="B1",
            reliability="B",
            title="Observed troop departures",
            content_hash="one",
        ),
        replace(
            evidence()[1],
            credibility=1,
            grade="A1",
            title="Satellite imagery shows vacant camp",
            content_hash="two",
        ),
    )
    assert quality_of_information(items).confidence_ceiling is Confidence.HIGH
    assert (
        quality_of_information([replace(i, credibility=2) for i in items]).confidence_ceiling
        is Confidence.MODERATE
    )
    data = sound_body()
    data["key_judgements"][0].update(confidence="high", contradicting_evidence=["E3"])
    result = validate_body(
        parse_body(data), frozenset(), {}, evidence_items=(*items, evidence()[2])
    )
    assert result.body.key_judgements[0].confidence is Confidence.LOW


def test_ambiguous_support_and_compound_judgements_require_review() -> None:
    data = sound_body()
    data["key_judgements"][0].update(
        contradicting_evidence=["E1"],
        statement="We assess it is highly likely that troops leave. Talks fail.",
    )
    assert {"citation", "structure"} <= {f.rule for f in checked(data).errors}


async def test_empty_model_output_retries_and_cannot_become_ready() -> None:
    gateway = ScriptedGateway("{}", "{}")
    profile = LlmProfile(
        uuid4(),
        "Scripted",
        "http://localhost:11434/v1",
        "test",
        "encrypted",
        "hint",
        frozenset({LlmRole.ASSESSMENT}),
        2000,
        0.1,
        True,
        NOW,
        NOW,
    )
    draft = await draft_body(
        gateway,
        profile,
        "test-key",
        TEMPLATES["intsum"],
        ReportHeader("intsum", "Test", {}, NOW, NOW, NOW),
        None,
        quality_of_information(evidence()),
        evidence(),
        (),
    )
    assert draft.attempts == 2 and draft.body is None and draft.has_errors
    assert "missing" in gateway.requests[1].messages[1].content


async def test_model_retry_repairs_unknown_citations_and_uses_frozen_grades() -> None:
    bad = sound_body()
    bad["key_judgements"][0]["supporting_evidence"] = ["invented"]
    gateway = ScriptedGateway(json.dumps(bad), json.dumps(sound_body()))
    profile = LlmProfile(
        uuid4(),
        "Scripted",
        "http://localhost:11434/v1",
        "test",
        "encrypted",
        "hint",
        frozenset({LlmRole.ASSESSMENT}),
        2000,
        0.1,
        True,
        NOW,
        NOW,
    )
    draft = await draft_body(
        gateway,
        profile,
        "test-key",
        TEMPLATES["intsum"],
        ReportHeader("intsum", "Test", {}, NOW, NOW, NOW),
        None,
        quality_of_information(evidence()),
        evidence(),
        (),
    )
    assert draft.attempts == 2 and not draft.has_errors and draft.body is not None
    assert draft.body.reporting[0].items[0].grade == "C3"
    assert "Unknown evidence invented" in gateway.requests[1].messages[1].content

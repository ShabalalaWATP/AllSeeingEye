"""New model citations must be exact IDs; historical reports keep their decoder."""

from copy import deepcopy

import pytest

from ase.adapters.llm.openai_responses import build_responses_payload
from ase.domain.llm import LlmMessage, LlmRequest
from ase.domain.report_input import parse_model_body
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import MAX_LIST, ReportParseError, parse_body
from ase.domain.validation import validate_body
from report_helpers import GOOD_BODY

FIELDS = ("supporting", "contradicting", "reporting", "assessment", "alternatives")


def citations(body):
    return {
        "supporting": body["key_judgements"][0]["supporting_evidence"],
        "contradicting": body["key_judgements"][0]["contradicting_evidence"],
        "reporting": body["reporting"][0]["items"][0]["evidence"],
        "assessment": body["assessment"][0]["evidence"],
        "alternatives": body["alternative_hypotheses"][0]["evidence"],
    }


def citation_schemas(schema):
    properties = schema["properties"]
    judgement = properties["key_judgements"]["items"]["properties"]
    reporting = properties["reporting"]["items"]["properties"]["items"]["items"]["properties"]
    return {
        "supporting": judgement["supporting_evidence"],
        "contradicting": judgement["contradicting_evidence"],
        "reporting": reporting["evidence"],
        "assessment": properties["assessment"]["items"]["properties"]["evidence"],
        "alternatives": properties["alternative_hypotheses"]["items"]["properties"]["evidence"],
    }


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize(
    "invalid",
    [
        "E2 identifies the Statue",
        "E1, E2",
        "E0",
        "E01",
        "E1\n",
        " E1",
        "E1 ",
        "E\u0661",
        "e1",
        "A1",
    ],
)
def test_new_citations_reject_prose_and_noncanonical_ids_without_prefix_laundering(field, invalid):
    data = deepcopy(GOOD_BODY)
    citations(data)[field][:] = [invalid]
    with pytest.raises(ReportParseError, match="invalid identifier") as error:
        parse_model_body(data)
    assert invalid not in str(error.value)
    assert citations(data)[field] == [invalid]


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("label", ["E1", "E12", "E" + "1" * 31])
def test_exact_ids_and_existing_assumption_ids_remain_accepted(field, label):
    data = deepcopy(GOOD_BODY)
    citations(data)[field][:] = [label]
    parsed = parse_model_body(data)
    assert label in parsed.cited_labels()
    assert parsed.key_judgements[0].assumptions == ("A1",)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("invalid", [["E1"] * (MAX_LIST + 1), ["E" + "1" * 32]])
def test_citation_count_and_length_limits_are_not_relaxed(field, invalid):
    data = deepcopy(GOOD_BODY)
    citations(data)[field][:] = invalid
    with pytest.raises(ReportParseError):
        parse_model_body(data)


@pytest.mark.parametrize("field", FIELDS)
def test_only_contradicting_evidence_can_be_empty(field):
    data = deepcopy(GOOD_BODY)
    citations(data)[field].clear()
    if field == "contradicting":
        assert parse_model_body(data).key_judgements[0].contradicting_evidence == ()
    else:
        with pytest.raises(ReportParseError, match="number of items"):
            parse_model_body(data)


def test_native_payload_preserves_exact_id_patterns_and_existing_bounds_for_all_paths():
    request = LlmRequest(
        messages=(LlmMessage("user", "Draft from the supplied evidence."),),
        max_output_tokens=6000,
        temperature=0,
        reasoning_effort="max",
        json_schema=REPORT_BODY_SCHEMA,
        schema_name="report",
    )
    output = build_responses_payload("gpt-5.6-luna", request)["text"]["format"]
    assert output["strict"] is True
    for field, schema in citation_schemas(output["schema"]).items():
        assert schema["maxItems"] == MAX_LIST
        assert schema.get("minItems", 0) == (0 if field == "contradicting" else 1)
        assert schema["items"]["pattern"] == "^E[1-9][0-9]*$"
        assert schema["items"]["minLength"] == 1 and schema["items"]["maxLength"] == 32


@pytest.mark.parametrize("field", FIELDS)
def test_well_formed_but_unknown_ids_still_fail_membership_validation(field):
    data = deepcopy(GOOD_BODY)
    citations(data)[field][:] = ["E999"]
    result = validate_body(parse_model_body(data), frozenset({"E1", "E2", "E3"}), {})
    assert not result.passed and "E999" not in result.body.cited_labels()
    assert any(finding.rule == "citation" for finding in result.errors)


def test_historical_decoder_does_not_rewrite_descriptive_citations_into_valid_ids():
    data = deepcopy(GOOD_BODY)
    invalid = "E2 identifies the Statue"
    data["key_judgements"][0]["supporting_evidence"] = [invalid]
    historic = parse_body(data)
    assert historic.key_judgements[0].supporting_evidence == (invalid,)
    result = validate_body(historic, frozenset({"E1", "E2", "E3"}), {})
    assert not result.passed and result.body.key_judgements[0].supporting_evidence == ()

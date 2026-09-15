"""Actual model schemas must satisfy OpenAI's strict object contract recursively.

Optional values remain required keys whose value can be null. This local contract
does not replace provider integration tests or validate every supported JSON keyword.
"""

from copy import deepcopy

import pytest

from ase.adapters.llm.openai_responses import build_responses_payload
from ase.adapters.llm.translator import translation_request
from ase.application.admin.llm_testing import TEST_SCHEMA
from ase.application.conflict_screening.records import ScreeningInput, screening_schema
from ase.application.reports.challenge_models import PLAN_SCHEMA, REVIEW_SCHEMA
from ase.application.reports.claim_proposal_model import SCHEMA as CLAIM_SCHEMA
from ase.application.reports.plan_queries import planning_schema
from ase.application.reports.production_types import Totals
from ase.application.reports.replan_queries import make_replanner
from ase.application.research.photo_model import photo_assessment_schema
from ase.application.research.query_translation import translation_schema
from ase.domain.advocacy import ADVOCACY_SCHEMA
from ase.domain.direction import DIRECTION_SCHEMA
from ase.domain.llm import LlmMessage, LlmRequest
from ase.domain.report_input import parse_model_body
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import ChangeFromPrevious, ReportParseError, parse_body
from ase.domain.research import ResearchBatch
from evaluation_helpers import REPORT_ANSWER
from production_integration_helpers import production_job
from report_helpers import GOOD_BODY, ScriptedGateway
from test_continuation_review import item
from test_research_plan import QUERY


def assert_strict_objects(schema, path="$", *, root=True):
    if root:
        assert schema["type"] == "object"
    if not isinstance(schema, dict):
        return
    types = schema.get("type", [])
    if types == "object" or "object" in types or "properties" in schema:
        properties = schema["properties"]
        required = schema.get("required", [])
        assert schema.get("additionalProperties") is False, path
        assert isinstance(required, list) and all(isinstance(key, str) for key in required), path
        assert len(required) == len(set(required)), path
        assert set(required) == set(properties), (
            f"{path}: missing required properties {set(properties) - set(required)}"
        )
    for key, value in schema.items():
        if isinstance(value, dict):
            assert_strict_objects(value, f"{path}.{key}", root=False)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                assert_strict_objects(child, f"{path}.{key}[{index}]", root=False)


@pytest.mark.parametrize(
    "schema",
    [
        pytest.param(REPORT_BODY_SCHEMA, id="report-body"),
        pytest.param(DIRECTION_SCHEMA, id="direction"),
        pytest.param(ADVOCACY_SCHEMA, id="advocacy"),
        pytest.param(PLAN_SCHEMA, id="challenge-plan"),
        pytest.param(REVIEW_SCHEMA, id="challenge-review"),
        pytest.param(CLAIM_SCHEMA, id="claim-proposal"),
        pytest.param(TEST_SCHEMA, id="connection-test"),
        # The provider receives the strict projection, not the defaulted API model schema.
        pytest.param(photo_assessment_schema(), id="photo-geolocation"),
        pytest.param(translation_schema(("en", "fr"), 2), id="query-translation"),
        pytest.param(
            screening_schema([ScreeningInput("one", "Public report", "")]),
            id="conflict-screening",
        ),
        pytest.param(
            planning_schema(
                {
                    "candidate_slots": 3,
                    "task_slots": 4,
                    "allowed_sources": [{"id": "public-source"}],
                }
            ),
            id="research-planning",
        ),
    ],
)
def test_actual_structured_output_schemas_require_every_property(schema):
    assert_strict_objects(schema)


def test_native_report_payload_keeps_the_strict_schema():
    request = LlmRequest(
        messages=(LlmMessage("user", "Draft the report from supplied evidence."),),
        max_output_tokens=16_000,
        temperature=0,
        reasoning_effort="max",
        json_schema=REPORT_BODY_SCHEMA,
        schema_name="report_body",
    )
    payload = build_responses_payload("gpt-5.6-luna", request)
    output_format = payload["text"]["format"]
    assert output_format["strict"] is True
    assert output_format["schema"] == REPORT_BODY_SCHEMA
    assert_strict_objects(output_format["schema"])


@pytest.mark.parametrize("body", [GOOD_BODY, REPORT_ANSWER], ids=["report", "evaluation"])
def test_scripted_model_report_fixtures_match_current_wire_contract(body):
    assert parse_model_body(deepcopy(body)).key_judgements


async def test_actual_title_translation_schema(container, user):
    job = production_job(user, container.cipher)
    request = translation_request([("Titre public", "fr")], job.profile)
    assert_strict_objects(request.json_schema)


@pytest.mark.parametrize("has_evidence", [False, True])
async def test_actual_replan_and_continuation_schemas(container, user, has_evidence):
    job = production_job(user, container.cipher)
    gateway = ScriptedGateway("{}")

    async def lookup(role):
        return job.profile

    callback = await make_replanner(job, Totals(), gateway, container.cipher, lookup)
    assert callback is not None
    await callback(QUERY, ResearchBatch(items=(item(),) if has_evidence else ()), 10)
    assert len(gateway.requests) == 1
    request = gateway.requests[0]
    assert request.schema_name == ("research_continuation" if has_evidence else "research_replan")
    assert_strict_objects(request.json_schema)


@pytest.mark.parametrize("change", [None, *ChangeFromPrevious])
def test_report_change_value_remains_nullable_or_a_known_change(change):
    data = deepcopy(GOOD_BODY)
    for judgement in data["key_judgements"]:
        judgement["change_from_previous"] = change.value if change is not None else None
    parsed = parse_model_body(data)
    assert all(judgement.change_from_previous == change for judgement in parsed.key_judgements)


def test_missing_change_is_rejected_for_new_output_but_old_reports_still_load():
    data = deepcopy(GOOD_BODY)
    for judgement in data["key_judgements"]:
        judgement.pop("change_from_previous", None)
    with pytest.raises(ReportParseError, match="change_from_previous"):
        parse_model_body(data)
    assert all(
        judgement.change_from_previous is None for judgement in parse_body(data).key_judgements
    )


def test_unknown_change_is_not_coerced_to_no_change():
    data = deepcopy(GOOD_BODY)
    data["key_judgements"][0]["change_from_previous"] = "confirmed"
    with pytest.raises(ReportParseError, match="change_from_previous"):
        parse_model_body(data)

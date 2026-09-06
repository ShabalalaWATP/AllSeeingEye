"""Fixture and metric integrity for the standalone real-model evaluation harness."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from evaluations.__main__ import json_bytes, main
from evaluations.casebook import EvaluationCase, load_cases
from evaluations.human_review import human_metrics, review_template
from evaluations.metrics import citation_references, ratio, statements
from evaluations.pipeline import EvaluationProfile, RecordingGateway, evaluate_case

from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmRequest
from evaluation_helpers import REPORT_ANSWER, EvaluationGateway

PROFILE = EvaluationProfile(base_url="http://127.0.0.1:11434/v1", model="fixture-only-model")


def test_casebook_is_labelled_and_keeps_original_multilingual_content() -> None:
    cases = load_cases()
    assert len(cases) == 8
    assert len({case.fingerprint for case in cases}) == 8
    assert all(case.reference.human_review_status == "pending" for case in cases)
    assert all(case.reference.label_origin.startswith("Assistant-authored") for case in cases)
    translated = [event for case in cases for event in case.graded_events() if event.title_en]
    assert {event.language for event in translated} == {"fr", "de"}
    assert all(event.title != event.title_en for event in translated)
    unknown = next(case for case in cases if case.id == "unknown_provenance")
    assert not unknown.source_profiles()


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case.id)
async def test_each_case_uses_the_actual_producer_without_reference_leakage(
    case: EvaluationCase,
) -> None:
    data = case.model_dump(mode="json")
    data["reference"]["reference_facts"].append("REFERENCE-RUBRIC-MUST-NOT-REACH-MODEL")
    labelled = EvaluationCase.model_validate(data)
    gateway = RecordingGateway(EvaluationGateway(), max_calls=2)
    result = await evaluate_case(labelled, PROFILE, gateway, "fixture-api-secret")
    assert result["report"]["body"]["key_judgements"]
    assert result["report"]["analysis"]["assessment"]
    assert result["deterministic"]["final_citation_reference_validity"]["value"] == 1
    assert result["deterministic"]["human_unsupported_statement_rate"] is None
    assert "fixture-api-secret" not in json_bytes(result).decode()
    assert "REFERENCE-RUBRIC-MUST-NOT-REACH-MODEL" not in json.dumps(gateway.records)
    assert gateway.records[0]["schema_name"] == "report"
    assert (
        "Writing requirements and automated checks" in gateway.records[0]["messages"][0]["content"]
    )
    expected = case.reference.expected_declared_organisation_groups
    if expected is not None:
        assert result["deterministic"]["expected_declared_organisation_groups_match"]


async def test_raw_citation_errors_remain_visible_after_the_app_removes_them() -> None:
    body = deepcopy(REPORT_ANSWER)
    body["key_judgements"][0]["supporting_evidence"].append("E999")
    gateway = RecordingGateway(EvaluationGateway(json.dumps(body)), max_calls=2)
    result = await evaluate_case(load_cases()[0], PROFILE, gateway, "")
    metrics = result["deterministic"]
    assert metrics["raw_citation_reference_validity"]["value"] < 1
    assert metrics["final_citation_reference_validity"]["value"] == 1
    assert "E999" not in result["report"]["body"]["key_judgements"][0]["supporting_evidence"]
    assert len(gateway.records) == 2


async def test_direction_advocacy_and_global_call_budget_use_existing_stages() -> None:
    configured = PROFILE.model_copy(update={"direction": True, "advocacy": True})
    gateway = RecordingGateway(EvaluationGateway(), max_calls=6)
    result = await evaluate_case(load_cases()[0], configured, gateway, "")
    assert {record["schema_name"] for record in gateway.records} == {
        "direction",
        "report",
        "advocacy",
    }
    assert result["report"]["analysis"]["direction"]
    assert result["report"]["analysis"]["devils_advocacy"]
    limited = RecordingGateway(EvaluationGateway("not-json"), max_calls=1)
    failed = await evaluate_case(load_cases()[0], PROFILE, limited, "")
    assert failed["report"]["status"] == "failed"
    assert len(limited.records) == 1
    assert failed["deterministic"]["raw_report_json_parse_failures"] == 1
    assert failed["deterministic"]["final_citation_reference_validity"]["value"] is None
    with pytest.raises(LlmGatewayError, match="budget"):
        await limited.complete(PROFILE.base_url, "", PROFILE.model, LlmRequest((), 100, 0))


async def test_human_review_metrics_require_explicit_attributed_labels() -> None:
    case = await evaluate_case(
        load_cases()[0], PROFILE, RecordingGateway(EvaluationGateway(), 2), ""
    )
    results = {"run_id": "fixture-run", "cases": [case]}
    review = review_template(results)
    with pytest.raises(ValueError, match="reviewer"):
        human_metrics(results, review)
    review["reviewer"] = "Fixture reviewer"
    empty = human_metrics(results, review)
    assert empty["unsupported_statement_field_rate"]["value"] is None
    assert empty["citation_review_coverage"]["numerator"] == 0
    assert empty["counterevidence_review_coverage"]["numerator"] == 0
    unit = review["cases"][0]["statements"][0]
    unit["supported"] = False
    unit["citations"][0]["relationship_correct"] = False
    review["cases"][0]["counterevidence_adequately_addressed"] = False
    review["cases"][0]["required_caveats_addressed"] = True
    scored = human_metrics(results, review)
    assert scored["unsupported_statement_field_rate"]["value"] == 1
    assert scored["citation_relationship_correctness"]["value"] == 0
    assert scored["statement_review_coverage"]["denominator"] == 3
    assert scored["statement_review_coverage"]["numerator"] == 1
    assert scored["counterevidence_adequacy"]["value"] == 0
    assert scored["citation_review_coverage"]["numerator"] == 1
    assert scored["counterevidence_review_coverage"]["value"] == 1


@pytest.mark.parametrize(
    "change", ["run", "source", "case", "statement", "duplicate", "citation", "label"]
)
async def test_stale_or_invalid_review_is_rejected(change: str) -> None:
    case = await evaluate_case(
        load_cases()[0], PROFILE, RecordingGateway(EvaluationGateway(), 2), ""
    )
    results = {"run_id": "fixture-run", "cases": [case]}
    review = review_template(results)
    review["reviewer"] = "Fixture reviewer"
    unit = review["cases"][0]["statements"][0]
    if change == "run":
        review["run_id"] = "other"
    elif change == "source":
        review["label_source"] = "model"
    elif change == "case":
        review["cases"][0]["case_sha256"] = "other"
    elif change == "statement":
        unit["text"] = "Edited statement"
    elif change == "duplicate":
        review["cases"].append(review["cases"][0])
    elif change == "citation":
        unit["citations"][0]["label"] = "E999"
    else:
        unit["supported"] = "true"
    with pytest.raises(ValueError):
        human_metrics(results, review)


def test_structural_metrics_never_invent_a_denominator() -> None:
    assert ratio(0, 0)["value"] is None
    assert citation_references(
        {"supporting_evidence": ("E1", 7), "other": [{"evidence": ["E2"]}]}
    ) == ["E1", "E2"]
    units = statements(
        {
            "alternative_hypotheses": [
                {"text": "Another explanation.", "why_less_likely": "A reason.", "evidence": ["E1"]}
            ]
        }
    )
    assert len(units) == 1 and units[0]["text"] == "Another explanation. A reason."


def test_cli_validate_and_input_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate"]) == 0
    assert "8 synthetic cases" in capsys.readouterr().out
    with pytest.raises(SystemExit) as error:
        main(["validate", "--cases-dir", str(tmp_path)])
    assert error.value.code == 2
    profile = tmp_path / "secret-profile.json"
    profile.write_text(json.dumps({**PROFILE.model_dump(), "api_key": "must-not-be-echoed"}))
    with pytest.raises(SystemExit):
        main(["run", "--profile", str(profile), "--out", str(tmp_path / "out")])
    assert "must-not-be-echoed" not in capsys.readouterr().err


def test_cli_run_and_score_use_only_explicit_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = EvaluationGateway()
    monkeypatch.setattr("evaluations.__main__.OpenAiCompatibleGateway", lambda **kwargs: gateway)
    monkeypatch.setenv("ASE_DATABASE_URL", "sqlite+aiosqlite:///DO-NOT-OPEN.db")
    monkeypatch.setenv("ASE_EVAL_API_KEY", "fixture-secret")
    profile = tmp_path / "profile.json"
    profile.write_text(PROFILE.model_dump_json())
    output = tmp_path / "run"
    assert (
        main(
            [
                "run",
                "--profile",
                str(profile),
                "--case",
                "conflicting_reports",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    assert gateway.closed
    result_text = (output / "results.json").read_text()
    assert "fixture-secret" not in result_text
    review = json.loads((output / "review.json").read_text())
    review["reviewer"] = "Fixture reviewer"
    (output / "review.json").write_text(json.dumps(review))
    metrics_file = output / "human.json"
    assert (
        main(
            [
                "score",
                "--results",
                str(output / "results.json"),
                "--review",
                str(output / "review.json"),
                "--out",
                str(metrics_file),
            ]
        )
        == 0
    )
    metrics: dict[str, Any] = json.loads(metrics_file.read_text())
    assert metrics["unsupported_statement_field_rate"]["value"] is None
    assert not (Path.cwd() / "DO-NOT-OPEN.db").exists()

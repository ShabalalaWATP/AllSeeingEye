"""V01 runs actual pure contracts and detects deliberately wrong reference outcomes."""

import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import Any

import evaluations.v01.__main__ as cli
import httpx
import pytest
from evaluations.v01.__main__ import main
from evaluations.v01.contracts import check_case
from evaluations.v01.corpus import load_corpus
from evaluations.v01.reporting import evaluate, ratio
from evaluations.v01.schema import ContractCase

CORPUS = load_corpus()


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Offline V01 must not access the network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(httpx.Client, "request", denied)
    monkeypatch.setattr(httpx.AsyncClient, "request", denied)


@pytest.mark.parametrize("case", CORPUS.cases, ids=lambda case: case.id)
def test_frozen_contract_expectations(case: ContractCase) -> None:
    checks = check_case(case)
    assert checks
    assert all(item.passed for item in checks), [item for item in checks if not item.passed]


@pytest.mark.parametrize("case_id", ["conflict_02", "cyber_03", "economy_06", "custom_area_09"])
def test_wrong_reference_outcomes_fail_without_changing_production(case_id: str) -> None:
    case = next(case for case in CORPUS.cases if case.id == case_id)
    data = case.model_dump(mode="json")
    if case_id.endswith("02"):
        data["probes"][0]["expected_present"] = True
    elif case_id.endswith("03"):
        data["probes"][0]["expected_indicators"] = []
    elif case_id.endswith("06"):
        data["probes"][0]["expected_admitted"] = True
    else:
        data["edition"]["expected_state"] = "no_new_relevant_captured_evidence"
    assert any(not item.passed for item in check_case(ContractCase.model_validate(data)))


def test_numeric_unit_blind_spots_remain_explicit_human_gates() -> None:
    unit_cases = [case for case in CORPUS.cases if case.id.endswith("05")]
    assert len(unit_cases) == 6
    for case in unit_cases:
        assert check_case(case)[0].actual == ()
        assert any("blind spot" in item for item in case.known_pitfalls)
    report = evaluate(CORPUS)
    for value in report["unmeasured"].values():
        assert value["denominator"] == 0
        assert value["value"] is None
        assert value["reason"]
    assert report["human_review_status"] == "pending"
    assert report["execution"]["model_calls"] == report["execution"]["provider_requests"] == 0
    assert report["execution"]["external_cost_usd"] == 0
    assert len(report["by_domain_and_declared_depth"]) == 18


def test_metric_denominators_cover_only_executed_probes_and_edition_pairs() -> None:
    report = evaluate(CORPUS)
    assert report["case_count"] == report["passed_case_count"] == 60
    metrics = report["metrics"]
    assert metrics["exact_excerpt_presence"] == ratio(12, 12)
    assert metrics["literal_cue_contract"] == ratio(18, 18)
    assert metrics["publication_time_admission"] == ratio(12, 12)
    assert metrics["edition_state"] == ratio(24, 24)
    assert metrics["synthetic_projection_change_precision"] == ratio(12, 12)
    assert metrics["synthetic_projection_change_recall"] == ratio(12, 12)
    assert metrics["no_data_gap_classification"] == ratio(6, 6)
    assert evaluate(CORPUS, "held_out")["case_count"] == 12
    assert evaluate(CORPUS, "development")["case_count"] == 48
    assert ratio(0, 0) == {"numerator": 0, "denominator": 0, "value": None}


def test_precision_and_recall_expose_false_positive_and_false_negative_references() -> None:
    positive = next(case for case in CORPUS.cases if case.id == "cyber_09")
    negative = next(case for case in CORPUS.cases if case.id == "cyber_10")
    first, second = positive.model_dump(mode="json"), negative.model_dump(mode="json")
    first["edition"]["expected_state"] = "no_new_relevant_captured_evidence"
    second["edition"]["expected_state"] = "assessment_changed"
    corpus = replace(
        CORPUS, cases=(ContractCase.model_validate(first), ContractCase.model_validate(second))
    )
    report = evaluate(corpus)
    assert report["passed_case_count"] == 0
    assert report["metrics"]["synthetic_projection_change_precision"] == ratio(0, 1)
    assert report["metrics"]["synthetic_projection_change_recall"] == ratio(0, 1)


def test_offline_cli_validates_writes_new_results_and_refuses_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["validate"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["cases"] == 60 and summary["consecutive_edition_cases"] == 24
    output = tmp_path / "contracts.json"
    assert main(["contracts", "--split", "held_out", "--out", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["case_count"] == 12
    with pytest.raises(FileExistsError):
        main(["contracts", "--out", str(output)])


def test_cli_returns_failure_for_wrong_expectations(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = CORPUS.cases[0].model_dump(mode="json")
    data["probes"][0]["expected_present"] = False
    monkeypatch.setattr(
        cli,
        "load_corpus",
        lambda root: replace(
            CORPUS,
            cases=(ContractCase.model_validate(data),),
        ),
    )
    assert cli.main(["contracts"]) == 1
    assert json.loads(capsys.readouterr().out)["passed_case_count"] == 0

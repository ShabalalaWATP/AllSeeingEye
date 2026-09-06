"""Production research stages with explicit replay packets, not model quality claims."""

import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest
from evaluations.__main__ import main
from evaluations.casebook import EvaluationCase, load_cases
from evaluations.pipeline import EvaluationProfile, RecordingGateway, evaluate_case
from evaluations.replay import ResearchReplay
from pydantic import ValidationError

from ase.domain.llm import LlmRequest, LlmResult
from ase.domain.research import ResearchMode, ResearchQuery
from evaluation_helpers import REPORT_ANSWER, EvaluationGateway


def replay_case() -> EvaluationCase:
    data = load_cases()[0].model_dump(mode="json")
    assert len(data["events"]) >= 2
    data["replay"] = {
        "initial": [
            {"id": "initial", "event_keys": [data["events"][0]["key"]]},
            {"id": "offline", "status": "unavailable"},
        ],
        "challenge": [{"id": "contrary", "event_keys": [data["events"][1]["key"]]}],
    }
    data["reference"]["reference_facts"].append("HIDDEN-REFERENCE-SENTINEL")
    return EvaluationCase.model_validate(data)


class ResearchGateway(EvaluationGateway):
    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        if request.schema_name in {"challenge_plan", "challenge_reviews"}:
            self.requests.append(request)
            if request.schema_name == "challenge_plan":
                rows = [{"target": target, "terms": ["contradiction"]} for target in ("KJ1", "KJ2")]
            else:
                rows = [
                    {
                        "target": target,
                        "argument": "Independent verification remains absent.",
                        "evidence": ["E1"],
                        "lower_confidence": False,
                        "rationale": "Synthetic fixture limitations.",
                    }
                    for target in ("KJ1", "KJ2")
                ]
            return LlmResult(content=json.dumps({"judgements": rows}), model=model, latency_ms=1)
        answer = deepcopy(REPORT_ANSWER)
        second = deepcopy(answer["key_judgements"][0])
        second["id"] = "KJ2"
        second["statement"] = (
            "We assess it is unlikely that independent verification is established."
        )
        answer["key_judgements"].append(second)
        self.response = json.dumps(answer)
        return await super().complete(base_url, api_key, model, request)


def profile(mode: ResearchMode) -> EvaluationProfile:
    return EvaluationProfile(
        base_url="http://127.0.0.1:11434/v1",
        model="fixture-only",
        direction=True,
        advocacy=True,
        research_mode=mode,
        research_languages=("fr", "en"),
    )


async def test_detailed_replay_runs_collection_redraft_and_all_judgement_review() -> None:
    case = replay_case()
    gateway = RecordingGateway(ResearchGateway(), max_calls=12)
    result = await evaluate_case(case, profile(ResearchMode.DETAILED), gateway, "")
    analysis = result["report"]["analysis"]
    assert analysis["research"]
    assert analysis["citation_checks"]
    assert analysis["research_context"]
    challenge = analysis["challenge"]
    assert challenge["redrafted"]
    assert len(challenge["searches"]) == len(challenge["reviews"]) == 2
    schemas = [record["schema_name"] for record in gateway.records]
    assert 2 <= schemas.count("report") <= 4
    assert schemas.index("report") < schemas.index("challenge_plan")
    assert schemas.index("challenge_plan") < len(schemas) - 1 - schemas[::-1].index("report")
    assert "challenge_plan" in schemas and "challenge_reviews" in schemas
    assert "advocacy" not in schemas
    replay = result["collection_evaluation"]
    assert replay["kind"] == "synthetic_provider_replay"
    assert not replay["live_retrieval_evaluated"]
    assert not replay["query_relevance_evaluated"]
    assert [call["stage"] for call in replay["provider_calls"]] == [
        "initial",
        "initial",
        "challenge",
        "challenge",
    ]
    assert all(call["languages"] == ["fr", "en"] for call in replay["provider_calls"])
    assert len(result["report"]["evidence"]) == 2
    assert "HIDDEN-REFERENCE-SENTINEL" not in json.dumps(gateway.records)
    assert result["deterministic"]["raw_citation_reference_validity"]["value"] is None


async def test_quick_replay_does_not_seed_hidden_challenge_packet() -> None:
    case = replay_case()
    gateway = RecordingGateway(ResearchGateway(), max_calls=8)
    result = await evaluate_case(case, profile(ResearchMode.QUICK), gateway, "")
    assert len(result["report"]["evidence"]) == 1
    assert {call["stage"] for call in result["collection_evaluation"]["provider_calls"]} == {
        "initial"
    }
    hidden = case.events[1].title
    assert hidden not in json.dumps(gateway.records)


async def test_replay_preserves_production_request_budget() -> None:
    data = replay_case().model_dump(mode="json")
    data["replay"]["initial"] = [{"id": f"provider-{i}", "status": "empty"} for i in range(8)]
    case = EvaluationCase.model_validate(data)
    replay = ResearchReplay(case)
    batch = await replay.collection.collect(
        ResearchQuery(
            case.question,
            case.as_of - timedelta(hours=case.window_hours),
            case.as_of,
        )
    )
    assert len(replay.calls) == 6
    assert [receipt.status.value for receipt in batch.attempts][-2:] == ["budget_exhausted"] * 2


async def test_research_mode_requires_explicit_replay_before_any_model_calls() -> None:
    gateway = RecordingGateway(EvaluationGateway(), 2)
    with pytest.raises(ValueError, match="explicit case replay"):
        await evaluate_case(load_cases()[0], profile(ResearchMode.QUICK), gateway, "")
    assert not gateway.records


@pytest.mark.parametrize("fault", ["unknown", "duplicate", "unavailable_events"])
def test_invalid_replay_scenarios_are_rejected(fault: str) -> None:
    data = replay_case().model_dump(mode="json")
    packet = data["replay"]["initial"][0]
    if fault == "unknown":
        packet["event_keys"] = ["missing-key"]
    elif fault == "duplicate":
        data["replay"]["initial"].append(packet)
    else:
        packet["status"] = "unavailable"
    with pytest.raises(ValidationError):
        EvaluationCase.model_validate(data)


@pytest.mark.parametrize("languages", [(), ("bad language",), ("en",) * 9])
def test_research_languages_follow_production_validation(languages: tuple[str, ...]) -> None:
    # Repeated valid codes are normalised by production, but distinct excess codes fail.
    if languages == ("en",) * 9:
        languages = ("en", "fr", "de", "es", "pt", "ru", "uk", "ar", "ja")
    with pytest.raises(ValidationError):
        EvaluationProfile(
            base_url="http://localhost/v1", model="fixture", research_languages=languages
        )


def test_committed_replay_casebook_runs_through_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = ResearchGateway()
    monkeypatch.setattr("evaluations.__main__.OpenAiCompatibleGateway", lambda **kwargs: gateway)
    cases_dir = Path(__file__).parents[1] / "evaluations" / "research_cases"
    assert main(["validate", "--cases-dir", str(cases_dir)]) == 0
    configured = tmp_path / "profile.json"
    configured.write_text(profile(ResearchMode.DETAILED).model_dump_json())
    out = tmp_path / "results"
    assert (
        main(
            [
                "run",
                "--profile",
                str(configured),
                "--cases-dir",
                str(cases_dir),
                "--out",
                str(out),
                "--max-calls",
                "24",
            ]
        )
        == 0
    )
    results = json.loads((out / "results.json").read_text())
    assert len(results["cases"]) == 2
    assert gateway.closed
    correction = next(case for case in results["cases"] if case["case_id"] == "research_correction")
    assert correction["report"]["analysis"]["challenge"]["redrafted"]
    unavailable = next(
        case for case in results["cases"] if case["case_id"] == "research_unavailable"
    )
    assert not unavailable["report"]["evidence"]
    assert not unavailable["collection_evaluation"]["live_retrieval_evaluated"]

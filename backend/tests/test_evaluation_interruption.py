"""Interrupted evaluations retain the evidence needed to diagnose incomplete runs."""

import asyncio
import json
from pathlib import Path

import pytest
from evaluations.__main__ import parser, run_evaluation
from evaluations.pipeline import EvaluationProfile

from ase.domain.llm import LlmRequest
from evaluation_helpers import EvaluationGateway


@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
async def test_interrupted_case_preserves_calls_without_exception_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: type[BaseException]
) -> None:
    gateway = EvaluationGateway()
    monkeypatch.setattr("evaluations.__main__.OpenAiCompatibleGateway", lambda **kwargs: gateway)

    async def interrupted(case, configuration, recording, api_key):
        await recording.complete(
            configuration.base_url, api_key, configuration.model, LlmRequest((), 100, 0)
        )
        raise failure("private diagnostic must not be saved")

    monkeypatch.setattr("evaluations.__main__.evaluate_case", interrupted)
    profile = tmp_path / "profile.json"
    profile.write_text(
        EvaluationProfile(base_url="http://localhost:11434/v1", model="fixture").model_dump_json()
    )
    output = tmp_path / "run"
    args = parser().parse_args(["run", "--profile", str(profile), "--out", str(output)])
    with pytest.raises(failure):
        await run_evaluation(args)
    assert gateway.closed
    raw = (output / "results.json").read_text()
    result = json.loads(raw)
    assert result["status"] == "interrupted"
    assert result["active_case"]
    assert result["model_calls"] == 1
    assert len(result["model_call_records"]) == 1
    assert result["cases"] == []
    assert "private diagnostic" not in raw
    assert not (output / "review.json").exists()


async def test_research_cases_are_preflighted_before_creating_gateway_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_gateway(**kwargs):
        pytest.fail("Invalid replay configuration must not construct a model gateway")

    monkeypatch.setattr("evaluations.__main__.OpenAiCompatibleGateway", unexpected_gateway)
    profile = tmp_path / "profile.json"
    profile.write_text(
        EvaluationProfile(
            base_url="http://localhost:11434/v1", model="fixture", research_mode="detailed"
        ).model_dump_json()
    )
    output = tmp_path / "run"
    args = parser().parse_args(["run", "--profile", str(profile), "--out", str(output)])
    with pytest.raises(ValueError, match="replay scenarios"):
        await run_evaluation(args)
    assert not output.exists()

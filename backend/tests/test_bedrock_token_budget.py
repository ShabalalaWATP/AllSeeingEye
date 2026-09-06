"""Native provider-default reasoning retains the administrator's completion budget."""

from dataclasses import replace

import pytest

from ase.domain.llm import LlmProvider
from production_integration_helpers import production_job


@pytest.mark.parametrize("stage_limit", [1000, 1200, 2500, 4000])
async def test_native_completion_budget_is_not_silently_reduced(container, user, stage_limit):
    profile = replace(
        production_job(user, container.cipher).profile,
        provider=LlmProvider.BEDROCK,
        model="openai.gpt-oss-120b-1:0",
        reasoning_effort=None,
        max_output_tokens=16000,
    )
    assert profile.token_budget(stage_limit) == 16000
    assert replace(profile, max_output_tokens=640).token_budget(stage_limit) == 640
    assert replace(profile, max_output_tokens=40000).token_budget(stage_limit) == 32000
    legacy = replace(profile, provider=LlmProvider.OPENAI_COMPATIBLE, model="local")
    assert legacy.token_budget(stage_limit) == stage_limit

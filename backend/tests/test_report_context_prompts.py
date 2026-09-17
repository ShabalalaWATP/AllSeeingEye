"""Small final-context tasks retain evidence and provider settings within a lower cap."""

import json
from dataclasses import replace

import pytest

from ase.application.reports.sections.synthesis_contracts import (
    ALTERNATIVES,
    COLLECTION,
    CONTEXT,
    CONTEXT_PARTS,
    JUDGEMENTS,
)
from section_model_helpers import HEADER, PROFILE, Checkpoints, Gateway, run


@pytest.mark.parametrize("configured_limit", [8_000, 32_000])
async def test_small_context_requests_keep_settings_evidence_and_bounded_outputs(configured_limit):
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    profile = replace(PROFILE, max_output_tokens=configured_limit)
    header = replace(HEADER, scope={"research_mode": "quick"})

    draft = await run(gateway, checkpoints, profile=profile, header=header)

    assert draft.body and not draft.has_errors
    calls = {name: request for name, request, *_ in gateway.calls}
    assert CONTEXT not in calls
    assert {JUDGEMENTS, *CONTEXT_PARTS} <= calls.keys()
    for part in CONTEXT_PARTS:
        request = calls[part]
        assert request.max_output_tokens == min(configured_limit, 16_000)
        assert request.reasoning_effort == profile.reasoning_effort
        assert request.profile_id == profile.id and request.provider == profile.provider
        payload = json.loads(request.messages[1].content)
        assert payload["original_frozen_evidence"]
        assert payload["validated_judgements_not_evidence"]
        assert "500 to 900" not in request.messages[0].content
        assert "not evidence" in request.messages[0].content
        assert "untrusted data" in request.messages[0].content
    assert set(calls[ALTERNATIVES].json_schema["properties"]) == {
        "alternative_hypotheses",
        "indicators_and_warning",
    }
    assert set(calls[COLLECTION].json_schema["properties"]) == {
        "gaps",
        "collection_recommendations",
        "sourcing_statement",
    }
    assert calls[ALTERNATIVES].messages != calls[COLLECTION].messages

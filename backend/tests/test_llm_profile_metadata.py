"""Accounting identity remains internal on every supported provider transport."""

from dataclasses import replace
from uuid import UUID

from ase.adapters.llm.bedrock import build_payload as bedrock_payload
from ase.adapters.llm.openai_compatible import build_payload as chat_payload
from ase.adapters.llm.openai_responses import build_responses_payload
from ase.domain.llm import LlmProvider
from report_job_budget_helpers import REQUEST

PROFILE_ID = UUID("6a156b03-b426-48ca-a5aa-4b212b5cf53d")


def test_internal_profile_identity_does_not_change_openai_request_payloads():
    identified = replace(REQUEST, profile_id=PROFILE_ID)
    assert chat_payload("luna", identified) == chat_payload("luna", REQUEST)
    assert build_responses_payload("luna", identified) == build_responses_payload("luna", REQUEST)


def test_internal_profile_identity_does_not_change_bedrock_request_payload():
    original = replace(
        REQUEST, provider=LlmProvider.BEDROCK, reasoning_effort=None, json_schema=None
    )
    identified = replace(original, profile_id=PROFILE_ID)
    assert bedrock_payload(identified) == bedrock_payload(original)

"""Scripted model outputs for harness plumbing, with no claim of model accuracy."""

import json
from copy import deepcopy
from typing import Any

from ase.domain.llm import LlmRequest, LlmResult

REPORT_ANSWER: dict[str, Any] = {
    "key_judgements": [
        {
            "id": "KJ1",
            "statement": "We assess it is unlikely that this packet resolves the question.",
            "probability": "unlikely",
            "confidence": "low",
            "confidence_statement": (
                "Information base: one supplied item. Rigour: source limitations "
                "reviewed. Complexity and volatility: not assessed."
            ),
            "supporting_evidence": ["E1"],
            "contradicting_evidence": [],
            "assumptions": [],
            "change_from_previous": None,
            "indicators": [],
        }
    ],
    "reporting": [
        {
            "theme": "Packet",
            "items": [
                {"text": "A supplied report is available.", "evidence": ["E1"], "grade": "F6"}
            ],
        }
    ],
    "assessment": [
        {
            "heading": "Limitations",
            "text": "Independent verification is absent.",
            "evidence": ["E1"],
        }
    ],
    "assumptions": [],
    "alternative_hypotheses": [],
    "indicators_and_warning": {"watch_condition": "normal", "changes": []},
    "gaps": [{"text": "Independent verification is absent.", "eei": None}],
    "collection_recommendations": ["Obtain independent reporting."],
    "sourcing_statement": "This fixture packet does not establish independent verification.",
}


class EvaluationGateway:
    def __init__(self, response: str | None = None) -> None:
        self.response = response
        self.requests: list[LlmRequest] = []
        self.closed = False

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.requests.append(request)
        answer = self.response or json.dumps(deepcopy(REPORT_ANSWER))
        if request.schema_name == "direction":
            answer = json.dumps(
                {
                    "pir": "What does the packet establish?",
                    "sirs": ["Evidence limits"],
                    "eeis": ["Which claims are independently supported?"],
                    "search_terms": [],
                    "categories": ["news"],
                }
            )
        elif request.schema_name == "advocacy":
            answer = json.dumps(
                {
                    "argument": "The packet has limited scope.",
                    "evidence": ["E1"],
                    "lower_confidence": False,
                    "rationale": "No additional evidence.",
                }
            )
        return LlmResult(
            content=answer, model=model, latency_ms=1, prompt_tokens=20, completion_tokens=30
        )

    async def aclose(self) -> None:
        self.closed = True

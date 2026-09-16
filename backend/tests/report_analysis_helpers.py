"""Scaffolding for the dedicated analysis pass and the diagrams it may request."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any
from uuid import uuid4

from ase.application.ports.llm import LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.ports.section_checkpoints import SectionCheckpoint
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import TEMPLATES
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult, LlmRole
from ase.domain.reports import ReportHeader, parse_body
from feeds_helpers import NOW
from report_helpers import filled_store, good_body

ANALYSIS_SECTIONS = [
    {
        "heading": "Why the pressure on El Fasher matters now",
        "text": (
            "The reporting establishes a ground advance and only suggests an intent to hold "
            "the city. The most consequential driver is resupply along the Mellit road, "
            "which would have to be interdicted for the advance to stall."
        ),
        "evidence": ["E1", "E2"],
    },
    {
        "heading": "The competing explanation",
        "text": (
            "The same reporting is consistent with a raid rather than an offensive. A "
            "withdrawal within seventy-two hours would distinguish the two."
        ),
        "evidence": ["E2"],
    },
]

TIMELINE = {
    "kind": "timeline",
    "title": "Reported sequence around El Fasher",
    "caption": "Dates are source-reported and have not been independently verified.",
    "alt_text": (
        "Timeline of three reported events: an entry into the city, overnight artillery, "
        "and talks resuming."
    ),
    "unit": "",
    "columns": [],
    "nodes": [],
    "edges": [],
    "entries": [
        {"when": "3 September", "label": "Forces entered the city", "evidence": ["E1"]},
        {"when": "4 September", "label": "Artillery fire overnight", "evidence": ["E2"]},
        {"when": "5 September", "label": "Talks resumed", "evidence": ["E3"]},
    ],
    "rows": [],
    "series": [],
}

ACTOR_MAP = {
    "kind": "actor_map",
    "title": "Reported relationships",
    "caption": "",
    "alt_text": "Three actors linked by two reported relationships.",
    "unit": "",
    "columns": [],
    "nodes": [
        {"id": "N1", "label": "Advancing force", "detail": "", "evidence": ["E1"]},
        {"id": "N2", "label": "City garrison", "detail": "holding", "evidence": ["E2"]},
        {"id": "N3", "label": "Mediator", "detail": "", "evidence": ["E3"]},
    ],
    "edges": [
        {"source": "N1", "target": "N2", "label": "attacks", "evidence": ["E1"]},
        {"source": "N3", "target": "N2", "label": "engages", "evidence": ["E3"]},
    ],
    "entries": [],
    "rows": [],
    "series": [],
}

MATRIX = {
    "kind": "comparison_matrix",
    "title": "Accounts compared",
    "caption": "",
    "alt_text": "Two accounts compared across two columns.",
    "unit": "",
    "columns": ["Reported by", "Location given"],
    "nodes": [],
    "edges": [],
    "entries": [],
    "rows": [
        {"label": "Ground advance", "cells": ["One agency", "City centre"], "evidence": ["E1"]},
        {"label": "Artillery", "cells": ["One agency", "Not stated"], "evidence": ["E2"]},
    ],
    "series": [],
}

SERIES = {
    "kind": "quantitative_series",
    "title": "Reported incidents by day",
    "caption": "",
    "alt_text": "One series of three reported daily counts.",
    "unit": "incidents",
    "columns": [],
    "nodes": [],
    "edges": [],
    "entries": [],
    "rows": [],
    "series": [
        {
            "label": "Reported incidents",
            "points": [
                {"label": "3 Sep", "value": 2},
                {"label": "4 Sep", "value": 5},
                {"label": "5 Sep", "value": 1},
            ],
            "evidence": ["E1", "E2"],
        }
    ],
}

CAUSAL_CHAIN = {
    **ACTOR_MAP,
    "kind": "causal_chain",
    "title": "Reported chain",
    "alt_text": "Three linked steps in a reported chain.",
}


def analysis_payload(diagram: Any = None) -> str:
    return json.dumps({"sections": ANALYSIS_SECTIONS, "diagram": diagram})


class AnalysisGateway:
    """Answers the analysis call, or fails it in a way the stage must survive."""

    def __init__(self, *answers: str, failure: Exception | None = None) -> None:
        self.answers = list(answers)
        self.failure = failure
        self.requests: list[LlmRequest] = []

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        answer = self.answers.pop(0) if self.answers else analysis_payload()
        return LlmResult(
            content=answer, model=model, latency_ms=12.0, prompt_tokens=40, completion_tokens=30
        )


def gateway_error() -> LlmGatewayError:
    return LlmGatewayError("the provider refused the call")


def exhausted() -> LlmTokenBudgetExhausted:
    return LlmTokenBudgetExhausted(model="test-model", prompt_tokens=40, completion_tokens=12)


class MemoryCheckpoints:
    def __init__(self) -> None:
        self.saved: dict[tuple[str, str], SectionCheckpoint] = {}

    async def load(self, packet_digest: str, section_id: str) -> SectionCheckpoint | None:
        return self.saved.get((packet_digest, section_id))

    async def save(
        self, packet_digest: str, section_id: str, checkpoint: SectionCheckpoint
    ) -> None:
        self.saved[(packet_digest, section_id)] = checkpoint


def analysis_profile(**overrides: Any) -> LlmProfile:
    values: dict[str, Any] = {
        "id": uuid4(),
        "name": "Analysis",
        "base_url": "https://models.example.com",
        "model": "test-model",
        "api_key_encrypted": "encrypted",
        "api_key_hint": "1234",
        "roles": frozenset({LlmRole.ASSESSMENT}),
        "max_output_tokens": 30_000,
        "temperature": 0.1,
        "enabled": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return LlmProfile(**{**values, **overrides})


def analysis_inputs() -> tuple[ReportHeader, Any, Any]:
    evidence = select_evidence(filled_store(), {}, TEMPLATES["intsum"].strategy, now=NOW).items
    header = ReportHeader("intsum", "Test report", {}, NOW - timedelta(days=2), NOW, NOW)
    return header, parse_body(good_body()), evidence

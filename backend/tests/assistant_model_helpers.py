"""Fixtures for assistant request and response contracts."""

import json
from datetime import UTC, datetime
from uuid import UUID

from ase.domain.assistant import AssistantContext, AssistantQuestion, AssistantSource
from ase.domain.events import Point
from ase.domain.llm import LlmProfile, LlmResult, LlmRole, ReasoningEffort

NOW = datetime(2026, 9, 11, tzinfo=UTC)
PROFILE = LlmProfile(
    id=UUID(int=1),
    name="Selected provider",
    base_url="https://api.openai.com/v1",
    model="gpt-5.6-luna",
    api_key_encrypted="encrypted-test-marker",
    api_key_hint="test",
    roles=frozenset({LlmRole.DIRECTION}),
    max_output_tokens=32000,
    temperature=0.25,
    enabled=True,
    created_at=NOW,
    updated_at=NOW,
    reasoning_effort=ReasoningEffort.MAX,
)
SOURCE = AssistantSource(
    "E1",
    "event",
    "event-1",
    "source-1",
    "Observed activity",
    "https://example.org/evidence",
    None,
    NOW,
    Point(lat=51, lon=-1),
    "B2",
    "A supplied source summary",
    ("Category: maritime",),
)
CONTEXT = AssistantContext((SOURCE,), 20, 1, True, ("The context is capped.",))
QUESTION = AssistantQuestion("What is reported here?")


def paragraph(text="A reported observation.", kind="finding", citations=None):
    return {"kind": kind, "text": text, "citations": ["E1"] if citations is None else citations}


def response(*paragraphs):
    return json.dumps({"paragraphs": list(paragraphs or [paragraph()])})


class Cipher:
    def __init__(self):
        self.calls = []

    def decrypt(self, value):
        self.calls.append(value)
        return "decrypted-test-marker"


class Gateway:
    def __init__(self, content=None, error=None):
        self.result = LlmResult(
            content if content is not None else response(), "actual-model", 42, 80, 25
        )
        self.error = error
        self.calls = []

    async def complete(self, *args):
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.result

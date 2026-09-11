"""Deterministic section models and checkpoint storage, without provider traffic."""

import json
from copy import deepcopy
from dataclasses import replace

from ase.application.ports.llm import LlmTokenBudgetExhausted
from ase.application.reports.sections import draft_sections
from ase.application.reports.sections.synthesis_contracts import schema_for
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence import quality_of_information
from ase.domain.llm import LlmResult
from ase.domain.reports import ReportHeader
from assistant_model_helpers import PROFILE
from feeds_helpers import NOW
from test_report_integrity import evidence, sound_body

HEADER = ReportHeader("ask", "Frozen scope", {}, NOW, NOW, NOW)


def items(count=3):
    base = evidence()[0]
    return tuple(
        replace(base, label=f"E{index}", event_id=f"event-{index}", title=f"Observation {index}")
        for index in range(1, count + 1)
    )


def topic_body(labels):
    return {
        "reporting": [
            {
                "text": f"Original reporting from {labels[0]}.",
                "evidence": [labels[0]],
                "grade": "C3",
            }
        ],
        "assessment": [
            {
                "heading": "Topic",
                "text": f"Limited assessment based on {labels[0]}.",
                "evidence": [labels[0]],
            }
        ],
        "gaps": [],
    }


def synthesis_body(labels):
    body = sound_body()
    body.pop("reporting")
    body.pop("assessment")
    body["gaps"] = []
    body["key_judgements"] = [body["key_judgements"][0]]
    body["key_judgements"][0]["supporting_evidence"] = [labels[0]]
    body["alternative_hypotheses"] = []
    return body


def synthesis_part_body(part, labels):
    body = synthesis_body(labels)
    return {key: body[key] for key in schema_for(part)["properties"]}


class Checkpoints:
    def __init__(self):
        self.rows = {}
        self.writes = []

    async def load(self, digest, section_id):
        return deepcopy(self.rows.get((digest, section_id)))

    async def save(self, digest, section_id, checkpoint):
        self.rows[digest, section_id] = deepcopy(checkpoint)
        self.writes.append((digest, section_id, deepcopy(checkpoint)))


class Gateway:
    def __init__(self, checkpoints, overrides=None):
        self.checkpoints = checkpoints
        self.overrides = overrides or {}
        self.calls = []

    async def complete(self, base_url, key, model, request):
        payload = json.loads(request.messages[1].content)
        topic = payload["topic"]
        name = topic["id"] if topic else payload.get("synthesis_step", "synthesis")
        self.calls.append((name, request, base_url, key, model))
        assert any(
            section_id == name and row.status == "running"
            for (_, section_id), row in self.checkpoints.rows.items()
        )
        if name in self.overrides:
            override = self.overrides[name]
            if isinstance(override, BaseException):
                raise override
            content = override
        else:
            labels = topic["evidence_labels"] if topic else ["E1"]
            content = json.dumps(topic_body(labels) if topic else synthesis_part_body(name, labels))
        return LlmResult(content, "returned-model", 1, 10, 5)


def exhausted():
    return LlmTokenBudgetExhausted(
        model="returned-model", prompt_tokens=20, completion_tokens=32000
    )


async def run(gateway, checkpoints, evidence_items=None, **kwargs):
    selected = items() if evidence_items is None else evidence_items
    return await draft_sections(
        gateway,
        kwargs.pop("profile", PROFILE),
        "test-key-marker",
        TEMPLATES["ask"],
        kwargs.pop("header", HEADER),
        "What does the supplied evidence establish?",
        quality_of_information(selected),
        selected,
        kwargs.pop("previous", ()),
        checkpoints=checkpoints,
        **kwargs,
    )

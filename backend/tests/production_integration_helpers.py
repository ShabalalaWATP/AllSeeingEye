"""Controlled production stages for integration and SQLite transaction regressions."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

from ase.application.ports.llm import LlmGatewayError, SecretCipher
from ase.application.reports.production import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import TEMPLATES
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult, LlmRole, LlmUsage
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User
from feeds_helpers import NOW
from report_helpers import good_body


class RecordingUsage:
    def __init__(self) -> None:
        self.rows: list[LlmUsage] = []

    async def add(self, usage: LlmUsage) -> None:
        self.rows.append(usage)

    async def list_recent(self, limit: int) -> list[LlmUsage]:
        return self.rows[-limit:]


class StageGateway:
    def __init__(
        self, before_call: Callable[[], None] = lambda: None, fail_stage: str = ""
    ) -> None:
        self.before_call = before_call
        self.fail_stage = fail_stage
        self.calls: list[str] = []

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.before_call()
        self.calls.append(request.schema_name)
        if request.schema_name == self.fail_stage:
            raise LlmGatewayError("Controlled model failure")
        responses = {
            "direction": {
                "pir": "What changed?",
                "sirs": [],
                "eeis": [],
                "search_terms": [],
                "categories": [],
            },
            "report": good_body(
                key_judgements=[
                    {**good_body()["key_judgements"][0], "supporting_evidence": ["E1"]}
                ],
                reporting=[
                    {
                        "theme": "Observed activity",
                        "items": [
                            {
                                "text": "The source reported activity.",
                                "evidence": ["E1"],
                                "grade": "A1",
                            }
                        ],
                    }
                ],
                assessment=[
                    {
                        "heading": "Trajectory",
                        "text": "Activity remains a concern.",
                        "evidence": ["E1"],
                    }
                ],
                alternative_hypotheses=[],
            ),
            "report_analysis": {
                "sections": [
                    {
                        "heading": "Why the activity matters now",
                        "text": "The reporting establishes movement and suggests intent.",
                        "evidence": ["E1"],
                    }
                ],
                "diagram": None,
            },
            "advocacy": {
                "argument": "The second source supports a pause.",
                "evidence": ["E2"],
                "lower_confidence": False,
                "rationale": "Independent contrary reporting.",
            },
            "entailment": {
                "assessments": [
                    {
                        "judgement_id": "KJ1",
                        "label": "E1",
                        "verdict": "supports",
                        "reason": "The extract states it.",
                    }
                ]
            },
            "contradiction_analysis": {"disagreements": []},
        }
        return LlmResult(json.dumps(responses[request.schema_name]), model, 10, 5, 3)


class BarrierResolver:
    def __init__(
        self, *, wait: bool = False, before_call: Callable[[], None] = lambda: None
    ) -> None:
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.before_call = before_call
        self.calls: list[str] = []
        if not wait:
            self.release.set()

    async def resolve(self, url: str) -> str | None:
        self.before_call()
        self.calls.append(url)
        self.entered.set()
        await self.release.wait()
        return url + "/resolved"


def production_job(actor: User, cipher: SecretCipher) -> Job:
    profile = LlmProfile(
        uuid4(),
        "Scripted",
        "http://localhost:11434/v1",
        "scripted",
        cipher.encrypt("test-key"),
        "-key",
        frozenset(LlmRole),
        2000,
        0,
        True,
        NOW,
        NOW,
    )
    return Job(
        actor,
        TEMPLATES["ask"],
        ReportRequest("ask", question="What changed?", devils_advocacy=True),
        profile,
        NOW,
        timedelta(hours=72),
        "Ask the Eye",
        {},
        None,
    )


def production_record(job: Job, version: ReportVersion) -> ReportRecord:
    return ReportRecord(
        version.report_id,
        job.template.id,
        job.title,
        job.scope,
        job.now - job.window,
        job.now,
        job.now,
        version.status,
        job.actor.id,
        job.now,
        version.number,
    )

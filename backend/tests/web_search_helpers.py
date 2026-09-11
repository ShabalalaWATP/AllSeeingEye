"""Synthetic native-search records, without live requests or application credentials."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ase.application.ports.web_search import WebSearchResult
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import template_for
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.research import ResearchMode, ResearchQuery
from ase.domain.users import Role, User
from ase.domain.web_research import WebCitation

NOW = datetime(2026, 9, 11, tzinfo=UTC)
TEXT = "Officials published a public climate report. Its conclusions need verification."
URL = "https://example.org/climate-report"
CITATION = WebCitation(URL, "Climate report", 0, 43)
RESULT = WebSearchResult(TEXT, (CITATION,), (URL,), "returned-model", 1, 25, 30, 15)
QUERY = ResearchQuery("What changed?", NOW - timedelta(days=1), NOW, research_web_search=True)


def native_response(**changes):
    return {
        "status": "completed",
        "model": "returned-model",
        "usage": {"input_tokens": 30, "output_tokens": 15},
        "output": [
            {
                "type": "web_search_call",
                "status": "completed",
                "action": {"type": "search", "sources": [{"url": URL}]},
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": TEXT,
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": URL,
                                "title": "Climate report",
                                "start_index": 0,
                                "end_index": 43,
                            }
                        ],
                    }
                ],
            },
        ],
        **changes,
    }


def profile(**changes):
    return replace(
        LlmProfile(
            uuid4(),
            "Selected direction",
            "https://api.openai.com/v1",
            "configured-model",
            "encrypted-fixture",
            "fixture",
            frozenset({LlmRole.DIRECTION}),
            8000,
            0.2,
            True,
            NOW,
            NOW,
            reasoning_effort="max",
            revision=3,
        ),
        **changes,
    )


def job():
    actor = User(
        uuid4(), "fixture@example.com", "Fixture", Role.USER, True, None, 0, None, None, NOW, None
    )
    return Job(
        actor,
        template_for("ask"),
        ReportRequest(
            "ask",
            question=QUERY.question,
            research_mode=ResearchMode.QUICK,
            research_web_search=True,
        ),
        profile(),
        NOW,
        timedelta(days=1),
        "Research question",
        {},
        None,
    )


class Admission:
    def __init__(self):
        self.active = True
        self.seen = []

    async def enabled(self, source_id):
        self.seen.append(source_id)
        return self.active

    @asynccontextmanager
    async def guard(self):
        yield


class Cipher:
    def decrypt(self, encrypted):
        assert encrypted == "encrypted-fixture"
        return "fixture-native-key"


class Gateway:
    def __init__(self, result=RESULT, after=None):
        self.result, self.after = result, after
        self.calls = []
        self.started = asyncio.Event()
        self.hold = False
        self.cancelled = False

    async def search(self, key, model, request):
        self.calls.append((key, model, request))
        self.started.set()
        if self.after:
            self.after()
        if self.hold:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

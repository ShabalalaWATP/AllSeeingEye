"""Synthetic retained observations and model/accounting controls for the Eye tests."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from ase.domain.events import Category, Event, GeoConfidence, Point, Reliability, freeze_attributes
from ase.domain.llm import LlmResult, ReasoningEffort
from llm_fixture_helpers import seed_legacy_profile

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
POINT = Point(140, 36)


def event(
    identifier="quake",
    *,
    category=Category.DISASTER,
    title="Earthquake near Tokyo, Japan",
    country="JP",
    source="usgs_earthquakes",
    point=POINT,
    attributes=None,
):
    return Event(
        identifier,
        source,
        category,
        category.value,
        title,
        NOW,
        NOW,
        Reliability.B,
        point=point,
        country_iso=country,
        geo_confidence=GeoConfidence.EXACT if point else GeoConfidence.NONE,
        attributes=freeze_attributes(attributes or {}),
    )


class Admission:
    def __init__(self):
        self.disabled = set()
        self.lock = asyncio.Lock()

    @asynccontextmanager
    async def guard(self):
        async with self.lock:
            yield

    async def enabled_many(self, identifiers):
        return {identifier: identifier not in self.disabled for identifier in identifiers}


async def nothing():
    return None


class Gateway:
    def __init__(self):
        self.calls = []
        self.after = nothing
        self.error = None
        self.tokens = (100, 50)
        self.content = json.dumps(
            {
                "paragraphs": [
                    {
                        "kind": "finding",
                        "text": "The source reports an earthquake.",
                        "citations": ["E1"],
                    },
                    {"kind": "gap", "text": "Coverage is incomplete.", "citations": []},
                ]
            }
        )

    async def complete(self, base_url, key, model, request):
        self.calls.append(request)
        await self.after()
        if self.error:
            raise self.error
        return LlmResult(self.content, "returned-fixture", 12, *self.tokens)


async def profile(container):
    chosen = await seed_legacy_profile(
        container,
        {
            "name": "Eye fixture",
            "base_url": "https://model.example.invalid/v1",
            "model": "gpt-5.6-luna",
            "api_key": "synthetic-assistant-key",
            "roles": ["assessment"],
            "max_output_tokens": 32000,
            "reasoning_effort": "max",
            "temperature": 0.2,
        },
    )
    chosen.reasoning_effort = ReasoningEffort.MAX
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.llm_profiles.save(chosen)
        await repos.uow.commit()
    return chosen

"""Private extracted-input and saved-parent fixtures, without parser or network calls."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from httpx import AsyncClient

from ase.application.ports.research_inputs import InputExtraction, StoredResearchInput
from ase.container import Container
from ase.domain.events import Category
from ase.domain.llm import LlmRequest, LlmResult
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.research import ResearchBatch, ResearchQuery
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_documents_helpers import document_records
from report_helpers import PROFILE, ScriptedGateway, good_body

DIRECTION = json.dumps(
    {
        "pir": "What changed?",
        "sirs": [],
        "eeis": [],
        "search_terms": ["private detail"],
        "categories": ["news"],
    }
)


class NoPublicCollection:
    def __init__(self) -> None:
        self.calls = 0

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.calls += 1
        raise AssertionError("Private input must not be sent to public collection")


class CallbackGateway(ScriptedGateway):
    def __init__(self, callback: Callable[[], Awaitable[None]] | None = None) -> None:
        super().__init__(DIRECTION, json.dumps(good_body()))
        self.callback = callback

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        if self.callback is not None and request.schema_name != "direction":
            callback, self.callback = self.callback, None
            await callback()
        return await super().complete(base_url, api_key, model, request)


async def model_setup(client: AsyncClient, container: Container, admin: User) -> NoPublicCollection:
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    container.llm = CallbackGateway()
    collection = NoPublicCollection()
    container.research = collection
    return collection


async def actor_headers(client: AsyncClient, actor: User, *, admin: bool = False) -> dict[str, str]:
    password = ADMIN_PASSWORD if admin else USER_PASSWORD
    return bearer(await login_token(client, actor.email, password))


def stored_input(container: Container, owner: User) -> StoredResearchInput:
    reservation = container.research_inputs.reserve(owner, "private-brief.txt")
    now = container.clock.now()
    # Distinct passages, not three copies of one headline: near-identical titles fold
    # into a single piece of reporting, which is not what these tests are about.
    passages = ("logistics note", "funding schedule", "site access record")
    events = tuple(
        make_event(
            f"private-extract-{index}",
            source_id="research-input-fixture",
            title=f"Private document {passages[index]}",
            summary="Private extracted source material.",
            published_at=now,
            observed_at=now,
            category=Category.NEWS,
            point=None,
        )
        for index in range(3)
    )
    extraction = InputExtraction(
        "private-brief.txt",
        "text/plain",
        "a" * 64,
        events,
        ("Source identity and document claims have not been verified.",),
    )
    return container.research_inputs.put(reservation, extraction)


async def saved_parent(
    container: Container, owner: User, team_id: UUID | None = None, *, private: bool = True
) -> tuple[ReportRecord, ReportVersion]:
    record, version = document_records(owner.id)
    record.team_id = team_id
    record.scope = {
        "question": "Original private question",
        "research_mode": "quick",
        "research_focus": "document" if private else "general",
        "research_languages": ["en"],
    }
    old = container.clock.now() - timedelta(days=30)
    version = replace(
        version,
        evidence=tuple(
            replace(item, published_at=old, captured_at=old, observed_at=old)
            for item in version.evidence
        ),
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


def report_payload(**overrides: object) -> dict[str, object]:
    return {
        "template": "ask",
        "question": "What does the private input establish?",
        "research_mode": "quick",
        "research_focus": "document",
        **overrides,
    }

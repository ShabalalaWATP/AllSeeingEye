"""Research collection is private, scoped and frozen into saved report versions."""

import json
from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.research_plan import ResearchPlan
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body


class CollectedResearch:
    def plan(self, query: ResearchQuery) -> ResearchPlan:
        return ResearchPlan(
            query.question, query.since, query.until, query.languages, (), 6, 45, 200
        )

    def __init__(self) -> None:
        self.queries: list[ResearchQuery] = []

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.queries.append(query)
        return ResearchBatch(
            items=tuple(
                make_event(
                    f"research-{index}",
                    title=f"Research finding {index}",
                    published_at=query.until - timedelta(hours=1),
                )
                for index in range(3)
            ),
            attempts=(
                CollectionAttempt(
                    "fixture",
                    "Synthetic collection",
                    CollectionStatus.COMPLETED,
                    3,
                    "Only fixture coverage; no real source verification.",
                    "fr",
                ),
            ),
        )


async def test_research_api_saves_receipt_without_publishing_live_items(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    research = CollectedResearch()
    container.research = research
    direction = json.dumps(
        {
            "pir": "What changed?",
            "sirs": ["Recent reporting"],
            "eeis": [],
            "search_terms": ["research"],
            "categories": ["news"],
        }
    )
    gateway = ScriptedGateway(direction, json.dumps(good_body()))
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "What changed?",
            "research_mode": "quick",
            "research_languages": ["fr"],
            "window_hours": 24,
        },
        headers=bearer(user_token),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert research.queries[0].languages == ("fr",)
    assert research.queries[0].terms == ("research",)
    assert len(payload["version"]["evidence"]) == 3
    assert payload["version"]["research"]["collected_items"] == 3
    assert payload["version"]["research"]["attempts"][0]["language"] == "fr"
    assert "Collection coverage" in payload["version"]["markdown"]
    assert "do not establish absence" in gateway.requests[1].messages[1].content
    assert container.store.get("research-0") is None
    report_id = payload["report"]["id"]
    saved = await client.get(f"/api/reports/{report_id}", headers=bearer(user_token))
    assert saved.status_code == 200
    assert saved.json()["version"]["research"] == payload["version"]["research"]


async def test_invalid_research_is_rejected_before_collection(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    research = CollectedResearch()
    container.research = research
    for fields in ({"question": " "}, {"question": "Test", "research_languages": []}):
        response = await client.post(
            "/api/reports",
            json={"template": "ask", "research_mode": "quick", **fields},
            headers=bearer(token),
        )
        assert response.status_code == 422
    assert not research.queries

"""A real report HTTP pipeline freezes native web context separately from graded evidence."""

from ase.application.ports.feeds import EventQuery
from ase.application.research.service import ResearchCollectionService
from ase.domain.web_research import WEB_SOURCE_ID
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway
from web_search_helpers import TEXT, URL, Gateway


async def test_web_context_flows_through_drafting_freezing_read_and_export(client, container, user):
    await seed_legacy_profile(
        container,
        {
            **PROFILE,
            "base_url": "https://api.openai.com/v1",
            "roles": ["assessment", "direction"],
        },
    )
    container.research = ResearchCollectionService(lambda _: ())
    container.llm = ScriptedGateway()
    native = Gateway()
    container.fresh_web_research._gateway = native
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/reports",
        headers=bearer(token),
        json={
            "template": "ask",
            "question": "What changed in the climate policy?",
            "countries": ["GB", "DE"],
            "research_mode": "quick",
            "research_web_search": True,
            "research_source_ids": [],
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    web = payload["version"]["research"]["web_research"]
    assert web["status"] == "completed" and web["synthesis"] == TEXT
    assert web["citations"][0]["url"] == URL and web["notice"].startswith("AI-generated")
    assert payload["report"]["scope"]["research_web_search"] is True
    assert payload["report"]["status"] == "needs_review"
    assert payload["version"]["evidence"] == []
    assert payload["version"]["quality"]["items"] == 0
    drafts = [request for request in container.llm.requests if request.schema_name == "report"]
    assert drafts and TEXT in drafts[0].messages[1].content
    assert "Do not cite it as E-labelled evidence" in drafts[0].messages[1].content
    report_id = payload["report"]["id"]
    fetched = await client.get(f"/api/reports/{report_id}", headers=bearer(token))
    assert fetched.status_code == 200
    assert fetched.json()["version"]["research"]["web_research"] == web
    exported = await client.get(f"/api/reports/{report_id}/markdown", headers=bearer(token))
    assert exported.status_code == 200
    assert "NEEDS REVIEW" in exported.text
    assert "The report draws on 0 retained source item(s)" in exported.text
    assert "## Fresh web context" not in exported.text
    assert TEXT not in exported.text
    assert URL not in exported.text
    assert web["returned_model"] not in exported.text
    assert "tool calls" not in exported.text.lower()
    assert len(native.calls) == 1
    async with container.session_factory() as session:
        usage = await container.repositories(session).llm_usage.list_recent(50)
    web_usage = [row for row in usage if row.purpose.endswith(":fresh_web_search")]
    assert len(web_usage) == 1 and web_usage[0].ok
    assert all(row.source_id != WEB_SOURCE_ID for row in container.store.query(EventQuery()))

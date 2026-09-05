"""Reports: evidence selection, rendering, generation with validation and retry, and the API."""

from __future__ import annotations

import json
from datetime import timedelta

from httpx import AsyncClient

from ase.application.dto import RateLimits
from ase.application.ports.feeds import EventQuery
from ase.application.reports.render import render_markdown
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import TEMPLATES, template_for
from ase.container import Container
from ase.domain.doctrine import Confidence
from ase.domain.events import Category
from ase.domain.evidence import quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.reports import ReportHeader, parse_body
from ase.domain.users import User
from ase.domain.validation import Finding, Severity
from feeds_helpers import NOW
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body


def test_selection_ranks_filters_and_flags() -> None:
    store = filled_store()
    profiles = {"fake_feed": SourceProfile("fake_feed", "Fake", "Fake feed", instrument=True)}
    selection = select_evidence(store, profiles, TEMPLATES["intsum"].strategy, now=NOW)
    labels = [(item.label, item.title) for item in selection.items]
    assert [label for label, _ in labels] == ["E1", "E2", "E3"]
    assert labels[0][1] == "Drone strike near Sumy"  # confirmed beats probably true
    assert selection.flagged == 1 and selection.considered == 4
    assert selection.items[0].instrument and selection.items[0].source_name == "Fake feed"
    assert [item.title for item in selection.items][2] == "Talks resume in Vienna"
    assert (
        select_evidence(store, {}, TEMPLATES["intsum"].strategy, now=NOW).items[0].source_name
        == "fake_feed"
    )
    scoped = select_evidence(
        store, profiles, TEMPLATES["intrep"].strategy, now=NOW, country_iso="UA"
    )
    assert [item.title for item in scoped.items] == [
        "Drone strike near Sumy",
        "Shelling in Kharkiv",
    ]
    only_news = select_evidence(
        store, profiles, TEMPLATES["intsum"].strategy, now=NOW, categories=[Category.NEWS]
    )
    assert [item.title for item in only_news.items] == ["Talks resume in Vienna"]
    capped = TEMPLATES["intsum"].strategy.__class__(frozenset(), 48, 40, 1)
    assert len(select_evidence(store, profiles, capped, now=NOW).items) == 1


def test_render_markdown_has_every_section() -> None:
    body = parse_body(good_body())
    store = filled_store()
    items = select_evidence(store, {}, TEMPLATES["intsum"].strategy, now=NOW).items
    header = ReportHeader(
        "intsum",
        "Intelligence summary: global",
        {"country": None},
        NOW - timedelta(days=2),
        NOW,
        NOW,
    )
    text = render_markdown(
        header,
        body,
        items,
        quality_of_information(items),
        [Finding("citation", Severity.WARNING, "KJ2", "Unknown evidence E9 removed")],
    )
    for heading in (
        "# Intelligence summary: global",
        "## Key judgements",
        "## Reporting",
        "## Assessment",
        "## Assumptions",
        "## Alternative hypotheses",
        "## Indicators and warning",
        "## Gaps and collection",
        "## Sourcing statement",
        "## Quality of information",
        "## Validator findings",
        "## Evidence annex",
    ):
        assert heading in text, heading
    assert "Probability: highly likely. Confidence: moderate." in text
    assert "| E1 | A1 | fake_feed |" in text
    assert "- warning: KJ2: Unknown evidence E9 removed" in text
    assert template_for("ask").needs_question


async def test_generate_read_export_and_delete(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    templates = await client.get("/api/reports/templates", headers=bearer(user_token))
    assert [t["id"] for t in templates.json()["items"]] == [
        "intsum",
        "intrep",
        "country_brief",
        "ask",
        "disaster_sitrep",
        "conflict_assessment",
        "aviation_activity",
        "maritime_activity",
        "cyber_summary",
    ]

    no_model = await client.post(
        "/api/reports", json={"template": "intsum"}, headers=bearer(user_token)
    )
    assert no_model.status_code == 409 and no_model.json()["error"]["code"] == "no_model"
    created = await client.post(
        "/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token)
    )
    assert created.status_code == 201

    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    judgements = good_body()["key_judgements"]
    fits = good_body(
        key_judgements=[judgements[0], {**judgements[1], "supporting_evidence": ["E2"]}]
    )
    gateway = ScriptedGateway(json.dumps(fits))
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json={"template": "intrep", "country": "ua", "window_hours": 12},
        headers=bearer(user_token),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    report_id = payload["report"]["id"]
    assert payload["report"]["status"] == "ready"
    assert payload["report"]["title"] == "Intelligence report: Ukraine"
    assert payload["report"]["scope"] == {
        "country": "UA",
        "categories": [],
        "question": None,
        "window_hours": 12,
        "devils_advocacy": False,
        "hazard": None,
        "conflict": None,
    }
    version = payload["version"]
    assert version["attempts"] == 1 and version["model"] == "llama3.1:8b"
    assert version["prompt_tokens"] == 50 and version["completion_tokens"] == 20
    assert [item["label"] for item in version["evidence"]] == ["E1", "E2"]
    assert version["quality"]["items"] == 2 and version["quality"]["confidence_ceiling"] in (
        "low",
        "moderate",
        "high",
    )
    assert version["body"]["key_judgements"][0]["probability"] == "highly_likely"
    assert any(f["rule"] == "citation" for f in version["findings"])  # E3 and E9 were unknown here
    assert not any(f["severity"] == "error" for f in version["findings"])
    assert "## Evidence annex" in version["markdown"]
    prompt = gateway.requests[0]
    assert prompt.json_schema is not None and prompt.messages[0].role == "system"
    assert "E1 [" in prompt.messages[1].content and "Kharkiv" in prompt.messages[1].content
    assert "sk-local" not in prompt.messages[1].content

    listed = await client.get("/api/reports", headers=bearer(admin_token))
    assert [item["id"] for item in listed.json()["items"]] == [report_id]
    fetched = await client.get(f"/api/reports/{report_id}", headers=bearer(admin_token))
    assert fetched.status_code == 200 and fetched.json()["version"]["number"] == 1
    assert (
        await client.get(f"/api/reports/{report_id}?version=2", headers=bearer(admin_token))
    ).status_code == 404
    markdown = await client.get(f"/api/reports/{report_id}/markdown", headers=bearer(user_token))
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert markdown.text.startswith("# Intelligence report: Ukraine")

    other = await client.post(
        "/api/reports", json={"template": "intsum"}, headers=bearer(admin_token)
    )
    other_id = other.json()["report"]["id"]
    forbidden = await client.delete(f"/api/reports/{other_id}", headers=bearer(user_token))
    assert forbidden.status_code == 403
    assert (
        await client.delete(f"/api/reports/{report_id}", headers=bearer(user_token))
    ).status_code == 204
    assert (
        await client.delete(f"/api/reports/{other_id}", headers=bearer(admin_token))
    ).status_code == 204
    assert (
        await client.get(f"/api/reports/{report_id}", headers=bearer(user_token))
    ).status_code == 404
    assert (
        await client.delete(f"/api/reports/{report_id}", headers=bearer(admin_token))
    ).status_code == 404


async def test_generation_faults_retry_limits_and_validation(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token))
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    bad = await client.post("/api/reports", json={"template": "nope"}, headers=bearer(token))
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_request"
    assert (
        await client.post("/api/reports", json={"template": "ask"}, headers=bearer(token))
    ).status_code == 422
    assert (
        await client.post("/api/reports", json={"template": "country_brief"}, headers=bearer(token))
    ).status_code == 422

    # Invalid JSON first, then a sound answer: two attempts, ready.
    container.llm = ScriptedGateway("not json", json.dumps(good_body()))
    ok = await client.post(
        "/api/reports", json={"template": "ask", "question": "What next?"}, headers=bearer(token)
    )
    assert ok.status_code == 201
    assert ok.json()["version"]["attempts"] == 2 and ok.json()["report"]["status"] == "ready"
    assert ok.json()["report"]["title"] == "Ask the Eye: What next?"

    # Two doctrine breaches in a row: stored for review with the findings attached.
    breach = good_body(
        key_judgements=[
            {**good_body()["key_judgements"][0], "statement": "It is very likely to intensify."}
        ]
    )
    container.llm = ScriptedGateway(json.dumps(breach), json.dumps(breach))
    review = await client.post("/api/reports", json={"template": "intsum"}, headers=bearer(token))
    assert review.json()["report"]["status"] == "needs_review"
    assert any(
        f["rule"] == "yardstick" and f["severity"] == "error"
        for f in review.json()["version"]["findings"]
    )
    assert "Your previous draft failed validation" in container.llm.requests[1].messages[1].content

    # The model never answers: the report is stored as failed, with the gateway error.
    container.llm = ScriptedGateway(
        "!The model endpoint answered 503: busy", "!The model endpoint answered 503: busy"
    )
    failed = await client.post("/api/reports", json={"template": "intsum"}, headers=bearer(token))
    assert failed.status_code == 201 and failed.json()["report"]["status"] == "failed"
    assert failed.json()["version"]["findings"][0]["rule"] == "model"
    usage = await client.get("/api/admin/llm/usage", headers=bearer(admin_token))
    assert (
        usage.json()["items"][0]["purpose"] == "report:intsum"
        and usage.json()["items"][0]["ok"] is False
    )

    container.limits = RateLimits(reports_per_user=1)
    container.llm = ScriptedGateway()
    fresh_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    first = await client.post(
        "/api/reports", json={"template": "intsum"}, headers=bearer(fresh_token)
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/reports", json={"template": "intsum"}, headers=bearer(fresh_token)
    )
    assert second.status_code == 429 and "retry-after" in second.headers
    assert quality_of_information([]).confidence_ceiling is Confidence.LOW


async def test_regeneration_adds_a_version_that_must_state_what_changed(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token))
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    container.llm = ScriptedGateway(json.dumps(good_body()))
    first = await client.post("/api/reports", json={"template": "intsum"}, headers=bearer(token))
    report_id = first.json()["report"]["id"]
    assert first.json()["version"]["number"] == 1

    # Without change markers the second version is stored for review.
    container.llm = ScriptedGateway(json.dumps(good_body()), json.dumps(good_body()))
    second = await client.post(f"/api/reports/{report_id}/versions", headers=bearer(token))
    assert second.status_code == 201, second.text
    assert second.json()["version"]["number"] == 2
    assert second.json()["report"]["latest_version"] == 2
    assert second.json()["report"]["status"] == "needs_review"
    assert any(f["rule"] == "change" for f in second.json()["version"]["findings"])
    prompt = container.llm.requests[0].messages[1].content
    assert "previous version's key judgements" in prompt
    assert "KJ1: We assess it is highly likely" in prompt

    # With them, the third version is ready and the earlier versions stay readable.
    judgements = [{**j, "change_from_previous": "unchanged"} for j in good_body()["key_judgements"]]
    container.llm = ScriptedGateway(json.dumps(good_body(key_judgements=judgements)))
    third = await client.post(f"/api/reports/{report_id}/versions", headers=bearer(token))
    assert third.json()["report"]["status"] == "ready"
    assert third.json()["version"]["number"] == 3
    assert (
        third.json()["version"]["body"]["key_judgements"][0]["change_from_previous"] == "unchanged"
    )
    latest = await client.get(f"/api/reports/{report_id}", headers=bearer(token))
    assert latest.json()["version"]["number"] == 3
    oldest = await client.get(f"/api/reports/{report_id}?version=1", headers=bearer(token))
    assert oldest.json()["version"]["number"] == 1
    listed = await client.get("/api/reports", headers=bearer(token))
    assert listed.json()["items"][0]["latest_version"] == 3
    missing = await client.post(
        "/api/reports/00000000-0000-4000-8000-000000000000/versions", headers=bearer(token)
    )
    assert missing.status_code == 404

"""Authenticated Eye answers and final source/session release boundaries."""

import asyncio
import json
from datetime import timedelta

import pytest

from ase.api.schemas_assistant import AssistantAnswerOut
from ase.application.assistant.service import MapAssistant
from assistant_helpers import Admission, Gateway, event, profile
from helpers import CSRF_COOKIE, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_assistant_requires_authentication(client):
    response = await client.post("/api/assistant/answer", json={"question": "Overview"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"question": " "},
        {"question": "x" * 2001},
        {"question": "Overview", "prior_questions": ["x" * 2001]},
        {"question": "Overview", "prior_questions": ["x"] * 5},
        {"question": "Overview", "scope": "viewport"},
        {"question": "Overview", "scope": "selected"},
        {
            "question": "Overview",
            "scope": "viewport",
            "bbox": {"west": 0, "south": 50, "east": 10, "north": 40},
        },
        {"question": "Overview", "team_id": "not-authorised"},
        {"question": "Overview", "selected": {"kind": "event", "id": "id"}},
        {
            "question": "Overview",
            "scope": "selected",
            "selected": {"kind": "event", "id": "x\u0000"},
        },
        {"question": "Overview", "prior_questions": [""]},
        {
            "question": "Overview",
            "scope": "selected",
            "selected": {"kind": "unsupported", "id": "x"},
        },
    ],
)
async def test_invalid_question_scope_rejected_before_model(body, client, user, container):
    gateway = Gateway()
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post("/api/assistant/answer", headers=bearer(token), json=body)
    assert response.status_code == 422, response.text
    assert not gateway.calls


async def test_source_backed_answer_uses_server_owned_links_and_no_store(client, user, container):
    await profile(container)
    container.store.upsert((event(),))
    gateway = Gateway()
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/assistant/answer", headers=bearer(token), json={"question": "Recent earthquakes"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["sources"][0]["record_id"] == "quake"
    assert data["paragraphs"][0]["citations"] == ["E1"]
    assert data["coverage"]["candidate_count"] >= data["coverage"]["matched_count"] >= 1
    assert response.headers["cache-control"] == "private, no-store"
    assert "synthetic-assistant-key" not in response.text
    assert data["scope"] == {"mode": "global", "bbox": None, "selected": None}
    assert data["coverage"]["selected_count"] == 1
    assert data["sources"][0]["source_id"] == "usgs_earthquakes"
    assert data["model"]["name"] == "returned-fixture"
    assert len(gateway.calls) == 1


async def test_missing_selected_record_returns_an_explicit_gap_without_a_model(
    client, user, container
):
    gateway = Gateway()
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    selected = {"kind": "event", "id": "unknown-public-record"}
    response = await client.post(
        "/api/assistant/answer",
        headers=bearer(token),
        json={"question": "Explain this item", "scope": "selected", "selected": selected},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["model"] is None and payload["sources"] == []
    assert payload["scope"] == {"mode": "selected", "bbox": None, "selected": selected}
    assert payload["paragraphs"][0]["kind"] == "gap"
    assert "does not establish absence" in payload["paragraphs"][0]["text"]
    assert response.headers["cache-control"] == "private, no-store"
    assert not gateway.calls


@pytest.mark.parametrize("transition", ["source_disabled", "logout", "expiry", "security_version"])
async def test_router_rechecks_authority_after_service_has_finished(
    transition,
    client,
    user,
    container,
    clock,
    monkeypatch,
):
    await profile(container)
    container.store.upsert((event(),))
    admission = Admission()
    container.source_admission = admission
    gateway = Gateway()
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    original = MapAssistant.execute

    async def changed_after_processing(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        if transition == "source_disabled":
            admission.disabled.add("usgs_earthquakes")
        elif transition == "logout":
            logout = await client.post(
                "/api/auth/logout",
                headers={"X-CSRF-Token": client.cookies[CSRF_COOKIE]},
            )
            assert logout.status_code == 204
        elif transition == "expiry":
            clock.advance(
                container.issuer.verify(token).expires_at - clock.now() + timedelta(seconds=1)
            )
        else:
            async with container.session_factory() as session:
                repos = container.repositories(session)
                current = await repos.users.get_by_id(user.id)
                current.security_version += 1
                await repos.users.save(current)
                await repos.uow.commit()
        return result

    monkeypatch.setattr(MapAssistant, "execute", changed_after_processing)
    response = await client.post(
        "/api/assistant/answer",
        headers=bearer(token),
        json={"question": "Recent earthquakes"},
    )
    assert response.status_code == (422 if transition == "source_disabled" else 401), response.text
    assert len(gateway.calls) == 1
    assert "The source reports an earthquake" not in response.text
    assert "Earthquake near Tokyo" not in response.text
    assert "synthetic-assistant-key" not in response.text
    assert not admission.lock.locked()


async def test_expiry_during_serialisation_cannot_release_the_answer(
    client,
    user,
    container,
    clock,
    monkeypatch,
):
    await profile(container)
    container.store.upsert((event(),))
    container.llm = Gateway()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    deadline = container.issuer.verify(token).expires_at
    original = AssistantAnswerOut.from_answer

    def expire_after_validating(cls, answer):
        payload = original(answer)
        clock.advance(deadline - clock.now() + timedelta(seconds=1))
        return payload

    monkeypatch.setattr(AssistantAnswerOut, "from_answer", classmethod(expire_after_validating))
    response = await client.post(
        "/api/assistant/answer",
        headers=bearer(token),
        json={"question": "Recent earthquakes"},
    )
    assert response.status_code == 401
    assert "The source reports an earthquake" not in response.text


async def test_http_disconnect_cancels_model_and_releases_capacity(app, client, user, container):
    await profile(container)
    container.store.upsert((event(),))
    started, cleaned = asyncio.Event(), asyncio.Event()
    gateway = Gateway()

    async def pending_model():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            cleaned.set()

    gateway.after = pending_model
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = json.dumps({"question": "Recent earthquakes"}).encode()
    delivered = False
    sent = []

    async def receive():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        await started.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "method": "POST",
        "scheme": "http",
        "path": "/api/assistant/answer",
        "raw_path": b"/api/assistant/answer",
        "query_string": b"",
        "root_path": "",
        "http_version": "1.1",
        "client": ("127.0.0.1", 42000),
        "server": ("test", 80),
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"authorization", f"Bearer {token}".encode()),
        ],
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=5)
    assert started.is_set() and cleaned.is_set()
    assert not container.assistant_capacity.active
    assert len(gateway.calls) == 1
    assert all(message.get("status") != 200 for message in sent)
    assert all(
        b"The source reports an earthquake" not in message.get("body", b"") for message in sent
    )
    async with container.session_factory() as session:
        usage = await container.repositories(session).llm_usage.list_recent(10)
    assert any(item.purpose == "map_assistant" and not item.ok for item in usage)

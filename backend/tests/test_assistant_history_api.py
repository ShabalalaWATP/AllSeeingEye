"""Saved chats are opt-in private snapshots, not trusted evidence."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ase.adapters.persistence.assistant_history import SqlAssistantHistory
from ase.adapters.persistence.assistant_history_models import AssistantConversationRow
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from report_documents_helpers import document_records


def _save_body(*, url: str | None = "https://example.org/record") -> dict:
    return {
        "title": "Earthquake notes",
        "turns": [
            {
                "question": "What happened?",
                "scope": "global",
                "time_window": "auto",
                "source_categories": ["earthquake"],
                "answer": {
                    "paragraphs": [
                        {"kind": "finding", "text": "A report was published.", "citations": ["E1"]}
                    ],
                    "sources": [
                        {
                            "id": "E1",
                            "kind": "event",
                            "record_id": "record-1",
                            "source_id": "example",
                            "title": "Example report",
                            "url": url,
                            "published_at": None,
                            "observed_at": None,
                            "point": None,
                            "grade": None,
                        }
                    ],
                    "scope": {"mode": "global", "bbox": None, "selected": None},
                    "coverage": {
                        "candidate_count": 1,
                        "matched_count": 1,
                        "selected_count": 1,
                        "source_count": 1,
                        "capped": False,
                        "notes": [],
                    },
                    "interpretation": {
                        "topics": ["earthquake"],
                        "countries": [],
                        "since": None,
                        "until": None,
                        "time_basis": "publication",
                        "notes": [],
                        "source_categories": ["earthquake"],
                    },
                    "continuation_id": "transient-continuation-secret",
                    "generated_at": datetime(2026, 9, 1, tzinfo=UTC).isoformat(),
                    "model": {"name": "private-model-name", "reasoning_effort": "high"},
                },
            }
        ],
    }


def _report_save_body(
    *,
    report_id: str = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    version: int = 3,
    version_id: str = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
) -> dict:
    body = _save_body()
    turn = body["turns"][0]
    turn["scope"] = "report"
    turn["source_categories"] = None
    turn["report"] = {"id": report_id, "version": version}
    turn["answer"]["scope"] = {"mode": "report", "bbox": None, "selected": None}
    turn["answer"]["report"] = {
        "id": report_id,
        "version_id": version_id,
        "version": version,
        "title": "Frozen report edition",
        "data_cutoff": "2026-09-01T00:00:00Z",
    }
    turn["answer"]["sources"][0]["kind"] = "report_claim"
    turn["answer"]["sources"][0]["source_id"] = f"report_version:{version_id}"
    return body


async def test_explicit_save_resume_replace_delete_and_strip_transient_metadata(
    client, user, container
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    assert (await client.get("/api/assistant/conversations", headers=headers)).json() == {
        "items": []
    }
    created = await client.post(
        "/api/assistant/conversations", headers=headers, json=_save_body(url="javascript:alert(1)")
    )
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "private, no-store"
    item = created.json()
    assert item["turns"][0]["answer"]["sources"][0]["url"] is None
    assert item["turns"][0]["answer"]["model"] is None
    assert item["turns"][0]["answer"]["continuation_id"] is None
    assert "user-controlled" in item["snapshot_notice"]
    async with container.session_factory() as session:
        stored = await session.get(AssistantConversationRow, UUID(item["id"]))
        assert stored is not None
        assert "private-model-name" not in stored.transcript
        assert "transient-continuation-secret" not in stored.transcript
        assert json.loads(stored.transcript)["turns"][0]["answer"]["sources"][0]["url"] is None
    loaded = await client.get(f"/api/assistant/conversations/{item['id']}", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json()["turns"] == item["turns"]
    listed = await client.get("/api/assistant/conversations", headers=headers)
    assert len(listed.json()["items"]) == 1
    updated_body = _save_body()
    updated_body["title"] = "Updated title"
    updated = await client.put(
        f"/api/assistant/conversations/{item['id']}", headers=headers, json=updated_body
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Updated title"
    deleted = await client.delete(f"/api/assistant/conversations/{item['id']}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.headers["cache-control"] == "private, no-store"
    missing = await client.get(f"/api/assistant/conversations/{item['id']}", headers=headers)
    assert missing.status_code == 404


async def test_report_scoped_save_resume_rechecks_exact_edition_access(client, user, container):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await container.repositories(session).uow.commit()
    body = _report_save_body(
        report_id=str(record.id), version=version.number, version_id=str(version.id)
    )
    created = await client.post("/api/assistant/conversations", headers=headers, json=body)
    assert created.status_code == 201, created.text
    saved = created.json()
    saved_turn = saved["turns"][0]
    assert saved_turn["scope"] == "report"
    assert saved_turn["report"] == {
        "id": str(record.id),
        "version": version.number,
    }
    assert saved_turn["answer"]["scope"]["mode"] == "report"
    assert saved_turn["answer"]["report"]["version"] == version.number
    assert saved_turn["answer"]["model"] is None
    assert saved_turn["answer"]["continuation_id"] is None
    loaded = await client.get(f"/api/assistant/conversations/{saved['id']}", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json()["turns"] == saved["turns"]

    mismatched = _report_save_body(
        report_id=str(record.id), version=version.number, version_id=str(version.id)
    )
    mismatched["turns"][0]["report"]["version"] = version.number + 1
    response = await client.post("/api/assistant/conversations", headers=headers, json=mismatched)
    assert response.status_code == 422
    assert "exact report edition" in response.text

    async with container.session_factory() as session:
        await container.repositories(session).reports.delete(record.id)
        await container.repositories(session).uow.commit()
    revoked = await client.get(f"/api/assistant/conversations/{saved['id']}", headers=headers)
    assert revoked.status_code == 404


async def test_owner_isolation_and_deactivation(client, user, container):
    owner_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/assistant/conversations", headers=bearer(owner_token), json=_save_body()
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    other = await create_user(container, email="other@example.com", password=USER_PASSWORD)
    other_token = await login_token(client, other.email, USER_PASSWORD)
    other_headers = bearer(other_token)
    assert (await client.get("/api/assistant/conversations", headers=other_headers)).json() == {
        "items": []
    }
    for method, body in (("get", None), ("put", _save_body()), ("delete", None)):
        url = f"/api/assistant/conversations/{item_id}"
        response = (
            await client.put(url, headers=other_headers, json=body)
            if body is not None
            else await getattr(client, method)(url, headers=other_headers)
        )
        assert response.status_code == 404, response.text
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.users.get_by_id(user.id)
        current.is_active = False
        await repos.users.save(current)
        await repos.uow.commit()
    assert (
        await client.get(f"/api/assistant/conversations/{item_id}", headers=bearer(owner_token))
    ).status_code == 401


async def test_saved_chat_limits_and_authentication(client, user):
    body = _save_body()
    assert (await client.post("/api/assistant/conversations", json=body)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    body["turns"] = body["turns"] * 9
    assert (
        await client.post("/api/assistant/conversations", headers=headers, json=body)
    ).status_code == 422
    body = _save_body()
    body["turns"][0]["question"] = "x" * 2001
    assert (
        await client.post("/api/assistant/conversations", headers=headers, json=body)
    ).status_code == 422


async def test_saved_chat_payload_and_per_user_count_are_bounded(client, user, container):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    body = _save_body()
    body["turns"][0]["answer"]["paragraphs"] = [
        {"kind": "finding", "text": "x" * 3_900, "citations": ["E1"]} for _ in range(4)
    ]
    body["turns"] *= 8
    too_large = await client.post("/api/assistant/conversations", headers=headers, json=body)
    assert too_large.status_code == 413, too_large.text
    now = container.clock.now()
    async with container.session_factory() as session:
        session.add_all(
            AssistantConversationRow(
                id=uuid4(),
                owner_id=user.id,
                title=f"Saved {number}",
                transcript='{"turns":[]}',
                transcript_bytes=12,
                turn_count=1,
                created_at=now,
                updated_at=now,
            )
            for number in range(30)
        )
        await session.commit()
    quota = await client.post("/api/assistant/conversations", headers=headers, json=_save_body())
    assert quota.status_code == 422
    assert "up to 30" in quota.text


async def test_expired_session_rolls_back_uncommitted_save(
    client, user, container, clock, monkeypatch
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    expiry = container.issuer.verify(token).expires_at
    original = SqlAssistantHistory.create

    async def expire_before_commit(self, *args, **kwargs):
        row = await original(self, *args, **kwargs)
        clock.advance(expiry - clock.now() + timedelta(seconds=1))
        return row

    monkeypatch.setattr(SqlAssistantHistory, "create", expire_before_commit)
    response = await client.post(
        "/api/assistant/conversations", headers=bearer(token), json=_save_body()
    )
    assert response.status_code == 401
    assert "A report was published" not in response.text
    async with container.session_factory() as session:
        assert await SqlAssistantHistory(session).count(user.id) == 0

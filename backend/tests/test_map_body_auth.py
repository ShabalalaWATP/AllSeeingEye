"""Saved-map authentication must finish before any large request body is read."""

import json
from uuid import uuid4

import pytest
from starlette.datastructures import Headers

from ase.api.middleware import BodySizeLimitMiddleware
from helpers import USER_PASSWORD, login_token
from test_map_views_api import body
from test_report_team_scope import save_team_report

SAVE_PATHS = [
    ("POST", "/api/map/views"),
    ("PATCH", "/api/map/views/7D3F2A9C-4B1E-4C8D-9A6F-1E2B3C4D5E6F"),
    ("PATCH", "/api/map/views/7d3f2a9c4b1e4c8d9a6f1e2b3c4d5e6f"),
    ("PATCH", "/api/map/views/{7d3f2a9c-4b1e-4c8d-9a6f-1e2b3c4d5e6f}"),
    ("PATCH", "/api/map/views/urn:uuid:7d3f2a9c-4b1e-4c8d-9a6f-1e2b3c4d5e6f"),
]


def map_scope(method, path, authorization=None):
    headers = [(b"content-type", b"application/json")]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "query_string": b"",
        "headers": headers,
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
        "root_path": "",
    }


async def assert_rejected_without_reading(app, method, path, authorization, root_path=""):
    messages = []

    async def receive():
        raise AssertionError("Saved-map body was read before authentication")

    async def send(message):
        messages.append(message)

    scope = map_scope(method, root_path + path, authorization)
    scope["root_path"] = root_path
    await app(scope, receive, send)
    assert messages[0]["status"] == 401
    headers = Headers(scope=messages[0])
    assert headers["cache-control"] == "no-store"
    assert headers["x-content-type-options"] == "nosniff"
    assert json.loads(messages[1]["body"])["error"]["code"] == "unauthenticated"


@pytest.mark.parametrize("method,path", SAVE_PATHS)
@pytest.mark.parametrize("authorization", [None, "Basic invalid", "Bearer invalid"])
async def test_missing_or_invalid_authentication_never_reads_map_body(
    app, method, path, authorization
):
    await assert_rejected_without_reading(app, method, path, authorization)


@pytest.mark.parametrize("method,path", SAVE_PATHS)
async def test_revoked_session_never_reads_map_body(app, client, container, user, method, path):
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.revoke_family(
            claims.family_id, container.clock.now()
        )
        await session.commit()
    await assert_rejected_without_reading(app, method, path, f"Bearer {token}")


@pytest.mark.parametrize("method,path", SAVE_PATHS)
async def test_larger_default_cap_and_root_path_cannot_skip_map_authentication(app, method, path):
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=10 * 1024 * 1024)
    await assert_rejected_without_reading(app, method, path, None, root_path="/mounted")


async def test_revocation_during_upload_is_rechecked_before_saving(app, client, container, user):
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    data = json.dumps(body(uuid4())).encode()
    reads = 0
    messages = []

    async def receive():
        nonlocal reads
        reads += 1
        if reads == 1:
            return {"type": "http.request", "body": data[:10], "more_body": True}
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                claims.family_id, container.clock.now()
            )
            await session.commit()
        return {"type": "http.request", "body": data[10:], "more_body": False}

    async def send(message):
        messages.append(message)

    await app(map_scope(*SAVE_PATHS[0], f"Bearer {token}"), receive, send)
    assert reads == 2
    assert messages[0]["status"] == 401


@pytest.mark.parametrize(
    "content_type", ["application/json", "application/vnd.map+json; charset=utf-8"]
)
async def test_invalid_json_and_schema_release_admission_and_keep_json_contract(
    client, container, user, content_type
):
    report = await save_team_report(container, user, None)
    token = await login_token(client, user.email, USER_PASSWORD)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    for invalid in (b"{", b"{}"):
        result = await client.post("/api/map/views", headers=headers, content=invalid)
        assert result.status_code == 422
        assert result.json()["error"]["code"] == "validation_error"
    created = await client.post(
        "/api/map/views", headers=headers, content=json.dumps(body(report.id)).encode()
    )
    assert created.status_code == 201, created.text


@pytest.mark.parametrize("identifier", ["hex", "braces", "urn"])
async def test_alternate_uuid_form_still_updates_saved_view(client, container, user, identifier):
    report = await save_team_report(container, user, None)
    token = await login_token(client, user.email, USER_PASSWORD)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/map/views", headers=headers, json=body(report.id))
    assert created.status_code == 201
    saved = created.json()
    view_id = saved["view"]["id"]
    path_id = {
        "hex": view_id.replace("-", ""),
        "braces": "{" + view_id + "}",
        "urn": "urn:uuid:" + view_id,
    }[identifier]
    updated = await client.patch(
        f"/api/map/views/{path_id}",
        headers=headers,
        json={
            "base_revision_id": saved["revision"]["id"],
            "version_number": 1,
            "title": "Updated",
            "state": saved["revision"]["state"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"]["number"] == 2

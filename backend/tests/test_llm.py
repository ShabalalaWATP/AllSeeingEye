"""LLM profiles: encryption at rest, the OpenAI-compatible gateway and the admin endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from httpx import AsyncClient

from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway, build_payload
from ase.adapters.security.cipher import CipherUnavailable, FernetCipher
from ase.application.ports.llm import LlmGatewayError
from ase.container import Container
from ase.domain.llm import LlmMessage, LlmRequest, LlmResult, key_hint, normalise_base_url
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token

PROFILE = {
    "name": "Local Llama",
    "base_url": "http://localhost:11434/v1/",
    "model": "llama3.1:8b",
    "roles": ["assessment", "direction"],
    "max_output_tokens": 2000,
    "temperature": 0.1,
    "enabled": True,
    "api_key": "sk-local-secret-1234",
}


class FakeGateway:
    def __init__(self, content: str = '{"ok": true}', fail: str | None = None) -> None:
        self.content = content
        self.fail = fail
        self.calls: list[tuple[str, str, str, LlmRequest]] = []

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.calls.append((base_url, api_key, model, request))
        if self.fail is not None:
            raise LlmGatewayError(self.fail)
        return LlmResult(content=self.content, model=model, latency_ms=12.5)


def test_cipher_round_trip_and_unavailability() -> None:
    cipher = FernetCipher("a" * 40)
    assert cipher.available
    token = cipher.encrypt("sk-secret")
    assert token != "sk-secret" and cipher.decrypt(token) == "sk-secret"
    other = FernetCipher("b" * 40)
    with pytest.raises(CipherUnavailable):
        other.decrypt(token)
    missing = FernetCipher(None)
    assert not missing.available
    with pytest.raises(CipherUnavailable):
        missing.encrypt("x")
    with pytest.raises(CipherUnavailable):
        missing.decrypt(token)
    assert not FernetCipher("short").available


def test_domain_helpers() -> None:
    assert normalise_base_url(" https://api.openai.com/v1/ ") == "https://api.openai.com/v1"
    assert normalise_base_url("http://localhost:11434/v1") == "http://localhost:11434/v1"
    assert normalise_base_url("http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434/v1"
    assert normalise_base_url("http://192.168.1.10:11434/v1") == "http://192.168.1.10:11434/v1"
    assert (
        normalise_base_url("http://host.docker.internal:11434/v1")
        == "http://host.docker.internal:11434/v1"
    )
    with pytest.raises(ValueError, match="HTTPS"):
        normalise_base_url("http://public.example/v1")
    with pytest.raises(ValueError, match="HTTPS"):
        normalise_base_url("http://93.184.216.34/v1")
    with pytest.raises(ValueError, match="HTTPS"):
        normalise_base_url("http://169.254.169.254/v1")
    with pytest.raises(ValueError, match="absolute"):
        normalise_base_url("ftp://models.example")
    with pytest.raises(ValueError, match="Credentials"):
        normalise_base_url("https://user:pw@models.example/v1")
    assert key_hint("sk-abcdef1234") == "1234"
    assert key_hint("abc") == "…"


async def test_gateway_calls_chat_completions_and_reports_faults() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: PLR0911
        seen.append(request)
        body = json.loads(request.content)
        if body["model"] == "bad-json":
            return httpx.Response(200, content=b"not json")
        if body["model"] == "empty":
            return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})
        if body["model"] == "no-choices":
            return httpx.Response(200, json={"choices": []})
        if body["model"] == "list":
            return httpx.Response(200, json=[1, 2])
        if body["model"] == "denied":
            return httpx.Response(401, json={"error": {"message": "bad key sk-local-secret"}})
        if body["model"] == "huge":
            return httpx.Response(200, content=b"x" * (4 * 1024 * 1024 + 1))
        if body["model"] == "down":
            raise httpx.ConnectError("refused")
        return httpx.Response(
            200,
            json={
                "model": "llama3.1:8b",
                "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 5},
            },
        )

    gateway = OpenAiCompatibleGateway(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    request = LlmRequest(
        messages=(LlmMessage("system", "Be brief."), LlmMessage("user", "Say ok.")),
        max_output_tokens=50,
        temperature=0.0,
        json_schema={"type": "object"},
        schema_name="probe",
    )
    result = await gateway.complete(
        "http://localhost:11434/v1", "sk-local-secret", "llama3.1:8b", request
    )
    assert result.content == '{"ok": true}'
    assert result.prompt_tokens == 20 and result.completion_tokens == 5
    assert result.latency_ms >= 0
    sent = seen[0]
    assert str(sent.url) == "http://localhost:11434/v1/chat/completions"
    assert sent.headers["authorization"] == "Bearer sk-local-secret"
    payload = json.loads(sent.content)
    assert payload["response_format"]["json_schema"]["name"] == "probe"
    assert payload["messages"][1] == {"role": "user", "content": "Say ok."}
    assert "response_format" not in build_payload("m", LlmRequest((), 10, 0.0))

    for model, message in [
        ("bad-json", "invalid JSON"),
        ("empty", "empty message"),
        ("no-choices", "no choices"),
        ("list", "other than an object"),
        ("huge", "allowed size"),
        ("down", "Could not reach"),
    ]:
        with pytest.raises(LlmGatewayError, match=message):
            await gateway.complete("http://localhost:11434/v1", "", model, request)
    with pytest.raises(LlmGatewayError) as denied:
        await gateway.complete("http://localhost:11434/v1", "sk-local-secret", "denied", request)
    assert "401" in str(denied.value)
    keyless = next(r for r in seen if json.loads(r.content)["model"] == "down")
    assert keyless.headers["authorization"] == ""
    await gateway.aclose()


async def test_admin_manages_profiles_without_ever_seeing_the_key(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (
        await client.get("/api/admin/llm/profiles", headers=bearer(user_token))
    ).status_code == 403

    empty = await client.get("/api/admin/llm/profiles", headers=bearer(token))
    assert empty.json() == {"items": [], "encryption_available": True}

    created = await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(token))
    assert created.status_code == 201, created.text
    profile = created.json()
    assert "api_key" not in profile and profile["api_key_hint"] == "1234"
    assert profile["base_url"] == "http://localhost:11434/v1"
    assert profile["roles"] == ["assessment", "direction"]
    profile_id = profile["id"]

    bad = await client.post(
        "/api/admin/llm/profiles", json={**PROFILE, "base_url": "ftp://x"}, headers=bearer(token)
    )
    assert bad.status_code == 422

    kept = await client.put(
        f"/api/admin/llm/profiles/{profile_id}",
        json={**PROFILE, "api_key": "", "enabled": False, "name": "Local Llama 2"},
        headers=bearer(token),
    )
    assert kept.status_code == 200
    assert kept.json()["api_key_hint"] == "1234" and kept.json()["enabled"] is False
    rotated = await client.put(
        f"/api/admin/llm/profiles/{profile_id}",
        json={**PROFILE, "api_key": "sk-new-key-9876"},
        headers=bearer(token),
    )
    assert rotated.json()["api_key_hint"] == "9876"

    gateway = FakeGateway()
    container.llm = gateway
    tested = await client.post(f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token))
    assert tested.status_code == 200
    assert {key: tested.json()[key] for key in ("ok", "latency_ms", "model", "error")} == {
        "ok": True,
        "latency_ms": 12.5,
        "model": "llama3.1:8b",
        "error": None,
    }
    assert tested.json()["revision"] == 3 and tested.json()["tested_config_hash"]
    assert gateway.calls[0][1] == "sk-new-key-9876"  # decrypted only for the call
    assert gateway.calls[0][3].json_schema is not None

    container.llm = FakeGateway(content="sure thing")
    not_json = await client.post(
        f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token)
    )
    assert not_json.json()["ok"] is False and "JSON" in not_json.json()["error"]
    container.llm = FakeGateway(content='{"ok": false}')
    wrong = await client.post(f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token))
    assert "expected object" in wrong.json()["error"]
    container.llm = FakeGateway(fail="The model endpoint answered 503: busy")
    down = await client.post(f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token))
    assert down.json()["ok"] is False and "503" in down.json()["error"]

    usage = await client.get("/api/admin/llm/usage?limit=10", headers=bearer(token))
    assert usage.status_code == 200
    items = usage.json()["items"]
    assert len(items) == 4 and items[0]["ok"] is False and items[-1]["ok"] is True
    assert items[0]["purpose"] == "connection_test"
    assert datetime.fromisoformat(items[0]["at"]).tzinfo is not None

    listed = await client.get("/api/admin/llm/profiles", headers=bearer(token))
    assert [item["name"] for item in listed.json()["items"]] == ["Local Llama"]

    gone = await client.delete(f"/api/admin/llm/profiles/{profile_id}", headers=bearer(token))
    assert gone.status_code == 204
    assert (await client.get("/api/admin/llm/profiles", headers=bearer(token))).json()[
        "items"
    ] == []
    missing = await client.post(f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token))
    assert missing.status_code == 404
    assert (
        await client.delete(f"/api/admin/llm/profiles/{profile_id}", headers=bearer(token))
    ).status_code == 404


async def test_profiles_need_an_encryption_key(
    client: AsyncClient, container: Container, admin: User
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    created = await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(token))
    profile_id = created.json()["id"]
    container.cipher = FernetCipher(None)
    listed = await client.get("/api/admin/llm/profiles", headers=bearer(token))
    assert listed.json()["encryption_available"] is False
    blocked = await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(token))
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "encryption_unavailable"
    rotated = await client.put(
        f"/api/admin/llm/profiles/{profile_id}", json=PROFILE, headers=bearer(token)
    )
    assert rotated.status_code == 409
    tested = await client.post(f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token))
    assert tested.status_code == 409
    # A rotated key makes the stored secret unreadable: the test reports it, nothing crashes.
    container.cipher = FernetCipher("z" * 40)
    container.llm = FakeGateway()
    unreadable = await client.post(
        f"/api/admin/llm/profiles/{profile_id}/test", headers=bearer(token)
    )
    assert unreadable.status_code == 200
    assert unreadable.json()["ok"] is False and "encryption key" in unreadable.json()["error"]
    assert datetime.now(UTC).year >= 2026

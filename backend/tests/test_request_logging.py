"""Request IDs and production logs never capture private request/provider content."""

import asyncio
import json
import logging
import re

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from structlog.testing import capture_logs

from ase.api.request_logging import RequestLoggingMiddleware
from ase.infrastructure.logging import configure_logging
from ase.infrastructure.request_context import request_id
from ase.infrastructure.settings import Environment, Settings


@pytest.mark.parametrize("path", ["/api/health", "/api/me", "/api/missing"])
async def test_response_echoes_safe_id(client, path):
    response = await client.get(path, headers={"X-Request-ID": "support-1234"})
    assert response.headers["X-Request-ID"] == "support-1234"
    if response.is_error:
        assert response.json()["error"]["request_id"] == "support-1234"


@pytest.mark.parametrize("identifier", ["", "short", "x" * 65, "unsafe/id", "header value"])
async def test_invalid_request_id_is_replaced(client, identifier):
    response = await client.get("/api/health", headers={"X-Request-ID": identifier})
    assert re.fullmatch("[a-f0-9]{32}", response.headers["X-Request-ID"])


async def test_validation_body_has_matching_id(client):
    response = await client.post("/api/auth/login", json={})
    assert response.status_code == 422
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


async def test_parallel_requests_and_background_context_are_isolated(app: FastAPI):
    background = []

    async def probe():
        identifier = request_id()
        await asyncio.sleep(0)
        assert request_id() == identifier

        async def child():
            background.append(request_id())

        await asyncio.create_task(child())
        return {"id": request_id()}

    app.add_api_route("/api/probe", probe)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = await asyncio.gather(
            *[client.get("/api/probe", headers={"X-Request-ID": f"request-{i}"}) for i in range(5)]
        )
    assert [response.json()["id"] for response in responses] == [f"request-{i}" for i in range(5)]
    assert background == [None] * 5
    assert request_id() is None


async def test_unknown_route_and_exception_logs_exclude_private_content(app, client):
    async def boom():
        raise RuntimeError("private-provider-token")

    app.add_api_route("/api/boom", boom)
    with capture_logs() as logs:
        missing = await client.get("/api/private-unknown?token=private-query")
        response = await client.get("/api/boom", headers={"X-Request-ID": "support-1234"})
    assert missing.status_code == 404
    assert response.status_code == 500
    assert response.json()["error"]["request_id"] == "support-1234"
    completed = [item for item in logs if item["event"] == "request.complete"]
    assert len(completed) == 2
    assert completed[0]["route"] == "unmatched"
    assert completed[1]["status"] == 500
    assert completed[1]["request_id"] == "support-1234"
    assert "private-" not in json.dumps(logs)


@pytest.mark.parametrize("end", ["completed", "disconnected", "cancelled", "error"])
async def test_stream_lifecycle_does_not_buffer_or_duplicate_completion(end):
    sent = []

    async def streaming(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"first", "more_body": True})
        assert len(sent) == 2
        if end == "disconnected":
            await receive()
        elif end == "cancelled":
            raise asyncio.CancelledError
        elif end == "error":
            raise RuntimeError("private-provider-token")
        else:
            await send({"type": "http.response.body", "body": b"last"})

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    middleware = RequestLoggingMiddleware(streaming)
    with capture_logs() as logs:
        try:
            await middleware({"type": "http", "method": "GET", "headers": []}, receive, send)
        except (RuntimeError, asyncio.CancelledError):
            assert end in {"error", "cancelled"}
    assert len(logs) == 1
    assert logs[0]["outcome"] == end
    assert len([message for message in sent if message["type"] == "http.response.start"]) == 1
    assert request_id() is None


def test_stdlib_and_structlog_share_recursive_redaction(capsys):
    configure_logging(
        Settings(_env_file=None, env=Environment.PROD, jwt_secret=SecretStr("p" * 32))
    )
    details = {"nested": [{"authorization": "private-token", "value": 1}]}
    logging.getLogger("test.stdlib").info("stdlib", extra={"details": details})
    structlog.get_logger("test.structlog").info("structured", details=details)
    records = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert [record["event"] for record in records] == ["stdlib", "structured"]
    assert all(
        record["details"]["nested"][0]["authorization"] == "[redacted]" for record in records
    )
    assert all(record["level"] == "info" for record in records)
    assert details["nested"][0]["authorization"] == "private-token"


async def test_production_500_header_body_and_logs_share_identifier(capsys):
    configure_logging(
        Settings(_env_file=None, env=Environment.PROD, jwt_secret=SecretStr("p" * 32))
    )
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/api/boom")
    async def boom():
        raise RuntimeError("private-provider-token")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/boom", headers={"X-Request-ID": "support-1234"})
    records = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert [record["event"] for record in records] == ["unhandled_error", "request.complete"]
    assert {record["request_id"] for record in records} == {"support-1234"}
    assert response.headers["X-Request-ID"] == "support-1234"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.json()["error"]["request_id"] == "support-1234"
    assert "private-provider-token" not in json.dumps(records)

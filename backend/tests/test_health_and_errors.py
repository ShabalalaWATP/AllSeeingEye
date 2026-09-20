"""Liveness, readiness, headers, docs exposure and the error envelope."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from ase import __version__
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.app_factory import create_app
from ase.container import Container
from ase.infrastructure.settings import Environment, Settings


async def test_health_reports_version(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


async def test_ready_checks_the_database(client: AsyncClient) -> None:
    response = await client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_ready_reports_database_failure(app: FastAPI, tmp_path: Path) -> None:
    container: Container = app.state.container
    broken = create_engine(f"sqlite+aiosqlite:///{tmp_path}/missing/dir/broken.db")
    container.session_factory = create_session_factory(broken)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/ready")
    await broken.dispose()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"


async def test_security_headers_on_every_response(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    csp = response.headers["content-security-policy"]
    assert csp == "default-src 'none'; frame-ancestors 'none'"
    assert "cache-control" not in response.headers


async def test_no_store_on_auth_routes(client: AsyncClient) -> None:
    response = await client.get("/api/me")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


async def test_docs_hidden_outside_dev(client: AsyncClient) -> None:
    response = await client.get("/api/docs")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_docs_available_in_dev() -> None:
    settings = Settings(
        _env_file=None, env=Environment.DEV, database_url="sqlite+aiosqlite://", cookie_secure=False
    )
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/docs")
        assert response.status_code == 200
        assert "content-security-policy" not in response.headers
        schema = await client.get("/api/openapi.json")
        assert "/api/auth/login" in schema.json()["paths"]
    await app.state.container.dispose()


async def test_validation_error_envelope(client: AsyncClient) -> None:
    response = await client.post("/api/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert "email" in body["fields"]
    assert "password" in body["fields"]


async def test_method_not_allowed_uses_envelope(client: AsyncClient) -> None:
    response = await client.delete("/api/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "http_error"


async def test_unexpected_errors_are_masked(app: FastAPI) -> None:
    async def boom() -> None:
        msg = "kaboom"
        raise RuntimeError(msg)

    app.add_api_route("/api/boom", boom)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong on our side."}
    }


def test_prod_requires_a_strong_secret() -> None:
    with pytest.raises(ValueError, match="ASE_JWT_SECRET"):
        Settings(_env_file=None, env=Environment.PROD, jwt_secret=SecretStr("short"))
    settings = Settings(_env_file=None, env=Environment.PROD, jwt_secret=SecretStr("p" * 32))
    assert settings.cookie_secure is True
    assert settings.generated_secret is False


def test_dev_generates_a_secret_and_insecure_cookies() -> None:
    settings = Settings(_env_file=None, env=Environment.DEV)
    assert settings.generated_secret is True
    assert len(settings.jwt_secret_value) >= 32
    assert settings.cookie_secure is False
    assert settings.rate_limits.login_per_ip == 10


def test_webhook_setting_requires_https() -> None:
    with pytest.raises(ValueError, match="ASE_ALERT_WEBHOOK_URL"):
        Settings(
            _env_file=None,
            env=Environment.TEST,
            alert_webhook_url="http://93.184.216.34/hook",
        )

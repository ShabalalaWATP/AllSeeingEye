"""Body size cap, exception logging and token edge cases added after the security review."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import jwt
import pytest
import structlog
from httpx import AsyncClient
from pydantic import SecretStr

from ase.adapters.security.tokens import SecretsTokenGenerator
from ase.container import Container
from ase.domain.users import User
from ase.infrastructure.logging import configure_logging
from ase.infrastructure.settings import Environment, Settings
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_oversized_declared_body_is_refused(client: AsyncClient) -> None:
    padding = "x" * 70_000
    response = await client.post("/api/auth/login", json={"email": padding, "password": "p"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_oversized_streamed_body_is_refused(client: AsyncClient) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        for _ in range(8):
            yield b"{" + b" " * 10_000

    response = await client.post(
        "/api/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


async def test_normal_bodies_still_pass(client: AsyncClient, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 200


def test_prod_logging_renders_tracebacks_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(
        Settings(_env_file=None, env=Environment.PROD, jwt_secret=SecretStr("p" * 32))
    )
    log = structlog.get_logger("test")
    try:
        credentials = {
            "password": "synthetic-password-marker",
            "code": "synthetic-code-marker",
            "challenge_token": "synthetic-challenge-marker",
        }
        assert credentials
        msg = "boom"
        raise ValueError(msg)
    except ValueError:
        log.exception("failed", password="hunter2")
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["event"] == "failed"
    assert record["password"] == "[redacted]"
    rendered = json.dumps(record["exception"])
    assert "boom" in rendered
    assert "synthetic-password-marker" not in rendered
    assert "synthetic-code-marker" not in rendered
    assert "synthetic-challenge-marker" not in rendered


def test_dev_logging_survives_tracebacks(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(_env_file=None, env=Environment.DEV))
    log = structlog.get_logger("test")
    try:
        msg = "boom → arrow"
        raise ValueError(msg)
    except ValueError:
        log.exception("failed")
    out = capsys.readouterr().out
    assert "failed" in out
    assert "ValueError" in out


async def test_malformed_expiry_claim_is_unauthenticated(
    client: AsyncClient, user: User, container: Container
) -> None:
    claims = {
        "sub": str(user.id),
        "role": "user",
        "typ": "access",
        "iat": int(container.clock.now().timestamp()),
        "exp": "not-a-number",
        "jti": "x",
    }
    token = jwt.encode(claims, container.settings.jwt_secret_value, algorithm="HS256")
    response = await client.get("/api/me", headers=bearer(token))
    assert response.status_code == 401


def test_token_generator_default_length() -> None:
    # 48 random bytes, URL-safe base64 encoded, as the contract states.
    assert len(SecretsTokenGenerator().new_secret()) >= 64

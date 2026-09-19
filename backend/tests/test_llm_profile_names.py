"""Duplicate connection names are recoverable without changing saved connections."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.llm import SqlLlmProfileRepository
from ase.container import Container
from ase.domain.errors import Conflict
from ase.domain.llm import LlmProfile
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm import FakeGateway
from test_llm_connections import DRAFT, ROOT, activation, draft, proof


@pytest.mark.parametrize("operation", ["create", "rename"])
async def test_duplicate_name_returns_field_error_and_preserves_connections(
    client: AsyncClient, container: Container, admin: User, operation: str
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    active = await draft(client, headers, "OpenAI Luna")
    receipt = await proof(client, headers, active)
    applied = await client.put(
        f"{ROOT}/connections", headers=headers, json=activation(active, receipt)
    )
    assert applied.status_code == 200
    candidate = await draft(client, headers, "New model") if operation == "rename" else None
    before_profiles = (await client.get(f"{ROOT}/profiles", headers=headers)).json()
    before_connections = (await client.get(f"{ROOT}/connections", headers=headers)).json()

    path = f"{ROOT}/profiles" + (f"/{candidate['id']}" if candidate else "")
    rejected = await client.request(
        "PUT" if candidate else "POST",
        path,
        headers=headers,
        json={**DRAFT, "name": " OpenAI Luna ", "model": "replacement-model"},
    )
    assert rejected.status_code == 409, rejected.text
    error = rejected.json()["error"]
    assert error["code"] == "conflict"
    assert "name" in error["fields"] and "already" in error["message"]
    assert "llm_profiles" not in rejected.text
    assert DRAFT["api_key"] not in rejected.text
    assert (await client.get(f"{ROOT}/profiles", headers=headers)).json() == before_profiles
    assert (await client.get(f"{ROOT}/connections", headers=headers)).json() == before_connections

    # Correcting the name should be sufficient to retry successfully.
    retried = await client.request(
        "PUT" if candidate else "POST",
        path,
        headers=headers,
        json={**DRAFT, "name": "Replacement model", "model": "replacement-model"},
    )
    assert retried.status_code == (200 if candidate else 201), retried.text
    assert not retried.json()["is_bound"] and not retried.json()["is_tested"]


@pytest.mark.parametrize(
    ("detail", "expected"),
    [
        ('duplicate key value violates unique constraint "ix_llm_profiles_name"', Conflict),
        ('duplicate key value violates unique constraint "llm_profiles_pkey"', IntegrityError),
        ("NOT NULL constraint failed: llm_profiles.name", IntegrityError),
    ],
)
async def test_only_profile_name_uniqueness_is_translated(
    detail: str, expected: type[Exception]
) -> None:
    session = Mock(spec=AsyncSession)
    session.flush = AsyncMock(side_effect=IntegrityError("insert", {}, Exception(detail)))
    profile = LlmProfile(
        id=uuid4(),
        name="New model",
        base_url="http://localhost:11434/v1",
        model="model",
        api_key_encrypted="synthetic-ciphertext",
        api_key_hint="",
        roles=frozenset(),
        max_output_tokens=2000,
        temperature=0.2,
        enabled=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    with pytest.raises(expected):
        await SqlLlmProfileRepository(session).add(profile)

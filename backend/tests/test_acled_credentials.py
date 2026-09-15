"""ACLED refresh storage, migration 0056, container wiring and requirement status."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import SecretStr
from sqlalchemy import create_engine, inspect

from acled_helpers import CIPHER, FakeAcledHttp, MemoryStore
from ase.adapters.feeds.acled_tokens import AcledTokens
from ase.adapters.feeds.conflict_acled import AcledConnector
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.persistence.acled_credentials import SqlAcledCredentialStore
from ase.adapters.persistence.base import Base
from ase.application.ports.acled_credentials import StoredAcledRefreshToken
from ase.container import Container
from ase.container.acled import build_acled_tokens
from ase.container.source_requirements import source_requirements
from ase.infrastructure.settings import Settings
from feeds_helpers import NOW, FakeClock, FakeHttp

VERSIONS = Path(__file__).parents[1] / "alembic/versions"


def _migration() -> ModuleType:
    path = next(VERSIONS.glob("0056_*.py"))
    spec = importlib.util.spec_from_file_location("migration_0056", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _settings(**values: object) -> Settings:
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_migration_0056_matches_the_model_and_guards_retained_rotation() -> None:
    module = _migration()
    assert module.revision == "0056" and module.down_revision == "0054"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            context = MigrationContext.configure(
                connection,
                opts={
                    "include_object": lambda obj, name, kind, reflected, compare: (
                        name == "acled_credentials"
                        if kind == "table"
                        else getattr(getattr(obj, "table", None), "name", None)
                        == "acled_credentials"
                    )
                },
            )
            assert compare_metadata(context, Base.metadata) == []
            insert = sa.text("INSERT INTO acled_credentials VALUES (:id, 'ciphertext', :fp, :at)")
            at = datetime.now(UTC).isoformat()
            with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
                connection.execute(insert, {"id": 2, "fp": "f" * 64, "at": at})
            connection.execute(insert, {"id": 1, "fp": "f" * 64, "at": at})
            with pytest.raises(RuntimeError, match="rotated ACLED refresh token"):
                module.downgrade()
            connection.execute(sa.text("DELETE FROM acled_credentials"))
            module.downgrade()
            assert "acled_credentials" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()


async def test_sql_store_round_trips_a_single_row(container: Container) -> None:
    store = SqlAcledCredentialStore(container.session_factory, container.clock)
    assert await store.load() is None
    await store.save(StoredAcledRefreshToken("cipher-one", "a" * 64))
    await store.save(StoredAcledRefreshToken("cipher-two", "b" * 64))
    assert await store.load() == StoredAcledRefreshToken("cipher-two", "b" * 64)


async def test_container_store_survives_a_new_provider_instance(container: Container) -> None:
    store = SqlAcledCredentialStore(container.session_factory, container.clock)
    cipher = CIPHER
    grant = {
        "token_type": "Bearer",
        "expires_in": 86400,
        "access_token": "synthetic-access",
        "refresh_token": "synthetic-rotated",
    }
    token = SecretStr("synthetic-env-refresh")
    first: Any = FakeAcledHttp(grant)
    await AcledTokens(first, container.clock, token, store, cipher).credential()
    second: Any = FakeAcledHttp(grant | {"refresh_token": "synthetic-rotated-2"})
    await AcledTokens(second, container.clock, token, store, cipher).credential()
    assert second.refreshed == ["synthetic-rotated"]


async def test_builder_only_wires_a_configured_enabled_refresh_token(
    container: Container,
) -> None:
    assert container.acled_tokens is None
    args = (container.session_factory, container.cipher, container.clock)
    assert build_acled_tokens(_settings(), *args) is None
    assert build_acled_tokens(_settings(acled_refresh_token="  "), *args) is None
    disabled = _settings(acled_refresh_token="synthetic", feeds_disabled="acled_events")
    assert build_acled_tokens(disabled, *args) is None
    built = build_acled_tokens(_settings(acled_refresh_token="synthetic"), *args)
    assert isinstance(built, AcledTokens)
    await built.aclose()


def test_refresh_tokens_register_the_connector_and_disabled_still_wins() -> None:
    http: Any = FakeAcledHttp()
    feeds: Any = FakeHttp()
    provider = AcledTokens(http, FakeClock(NOW), SecretStr("synthetic"), MemoryStore(), CIPHER)
    connectors = build_connectors(feeds, FakeClock(NOW), acled_tokens=provider)
    by_id = {connector.spec.id: connector for connector in connectors}
    assert isinstance(by_id["acled_events"], AcledConnector)
    disabled = build_connectors(feeds, FakeClock(NOW), {"acled_events"}, acled_tokens=provider)
    assert "acled_events" not in {c.spec.id for c in disabled}


@pytest.mark.parametrize(
    ("values", "satisfied", "fragment"),
    [
        ({}, False, "password grant"),
        ({"acled_access_token": "synthetic-access"}, True, "expires after 24 hours"),
        ({"acled_refresh_token": "synthetic-refresh"}, True, "renew automatically"),
        (
            {"acled_refresh_token": "synthetic-refresh", "acled_access_token": "synthetic-access"},
            True,
            "renew automatically",
        ),
        ({"acled_refresh_token": "   "}, False, "password grant"),
    ],
)
def test_requirement_is_satisfied_by_either_setting(
    values: dict[str, str], satisfied: bool, fragment: str
) -> None:
    requirement = source_requirements(_settings(**values))["acled_events"]
    assert requirement.satisfied is satisfied
    assert requirement.origin == ("environment" if satisfied else "none")
    assert requirement.setting == "ASE_ACLED_REFRESH_TOKEN or ASE_ACLED_ACCESS_TOKEN"
    assert fragment in requirement.note
    assert "synthetic" not in requirement.note


def test_refresh_token_is_secret_in_settings() -> None:
    settings = _settings(acled_refresh_token="acled-refresh-fixture-secret")
    assert "acled-refresh-fixture-secret" not in repr(settings)
    assert "acled-refresh-fixture-secret" not in settings.model_dump_json()

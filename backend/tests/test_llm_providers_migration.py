"""Provider migration preserves tested bindings and refuses lossy credential downgrades."""

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.llm import SqlLlmProfileRepository
from ase.adapters.persistence.llm_bindings import SqlLlmBindingRepository
from ase.adapters.persistence.operational_models import ReportVersionRow
from ase.adapters.security.cipher import FernetCipher
from ase.application.model_routing import ModelRouting
from ase.domain.llm import TEXT_ROLES, LlmProvider, LlmRole
from ase.infrastructure.migrations import alembic_config
from test_llm_connections_migration import _database, _seed

TABLES = (
    "llm_profiles",
    "llm_usage",
    "reports",
    "report_versions",
    "llm_connection_bindings",
    "llm_binding_sequence",
)
MODEL_ARN = "arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/" + "a" * 160


def _snapshot(connection: sa.Connection) -> dict[str, list[dict[str, Any]]]:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    return {
        name: [dict(row) for row in connection.execute(sa.select(metadata.tables[name])).mappings()]
        for name in TABLES
    }


def _seed_tested_binding(connection: sa.Connection) -> dict[str, list[dict[str, Any]]]:
    _seed(connection)
    metadata = sa.MetaData()
    metadata.reflect(connection)
    profiles = metadata.tables["llm_profiles"]
    first = connection.execute(sa.select(profiles).order_by(profiles.c.name)).mappings().first()
    assert first is not None
    roles = sorted(role.value for role in TEXT_ROLES)
    # The exact pre-provider hash contract is frozen here, independently of current domain code.
    previous_hash = hashlib.sha256(
        json.dumps(
            (
                str(UUID(str(first["id"]))),
                first["revision"],
                first["name"],
                first["base_url"],
                first["model"],
                first["api_key_encrypted"],
                roles,
                first["max_output_tokens"],
                first["temperature"],
                first["reasoning_effort"],
            ),
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    now = datetime(2026, 9, 7, tzinfo=UTC)
    connection.execute(
        profiles.update()
        .where(profiles.c.id == first["id"])
        .values(
            roles=roles,
            tested_at=now,
            tested_revision=first["revision"],
            tested_config_hash=previous_hash,
            test_generation=7,
        )
    )
    report = connection.execute(sa.select(metadata.tables["reports"])).mappings().one()
    for revision, team in enumerate((None, report["team_id"]), 1):
        connection.execute(
            metadata.tables["llm_connection_bindings"]
            .insert()
            .values(
                scope_key="global" if team is None else f"team:{UUID(str(team))}",
                team_id=team,
                profile_id=first["id"],
                profile_revision=first["revision"],
                tested_config_hash=previous_hash,
                activated_at=now,
                activated_by=report["created_by"],
                revision=revision,
            )
        )
    connection.execute(metadata.tables["llm_binding_sequence"].update().values(value=2))
    return _snapshot(connection)


def _assert_preserved(connection: sa.Connection, original: dict[str, list[dict[str, Any]]]) -> None:
    current = _snapshot(connection)
    for name, rows in original.items():
        assert len(current[name]) == len(rows)
        key = "scope_key" if name == "llm_connection_bindings" else "id"
        by_key = {row[key]: row for row in current[name]}
        for row in rows:
            assert {field: by_key[row[key]][field] for field in row} == row


def _assert_schema(connection: sa.Connection, *, upgraded: bool) -> None:
    profiles = sa.Table("llm_profiles", sa.MetaData(), autoload_with=connection)
    versions = sa.Table("report_versions", sa.MetaData(), autoload_with=connection)
    assert profiles.c.model.type.length == (2048 if upgraded else 120)
    assert versions.c.model.type.length == (2048 if upgraded else 120)
    if upgraded:
        assert profiles.c.provider.nullable is False
        assert isinstance(profiles.c.api_key_encrypted.type, sa.Text)
        assert set(connection.scalars(sa.select(profiles.c.provider))) == {"openai_compatible"}
    else:
        assert "provider" not in profiles.c
        assert profiles.c.api_key_encrypted.type.length == 2048


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
async def test_provider_migration_keeps_legacy_test_proof_and_routing(
    dialect: str, tmp_path: Path
) -> None:
    async with _database(dialect, tmp_path) as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0017")
        # Alembic uses another engine; reconnect after DDL to avoid stale asyncpg plans.
        engine = create_async_engine(url, poolclass=sa.NullPool)
        try:
            async with engine.begin() as connection:
                original = await connection.run_sync(_seed_tested_binding)
            await asyncio.to_thread(command.upgrade, config, "0018")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                await connection.run_sync(lambda sync: _assert_schema(sync, upgraded=True))
            async with async_sessionmaker(engine)() as session:
                router = ModelRouting(
                    SqlLlmProfileRepository(session), SqlLlmBindingRepository(session)
                )
                team = UUID(str(original["reports"][0]["team_id"]))
                for destination in (None, team):
                    selection = await router.snapshot(team_id=destination)
                    profile = selection.required(LlmRole.ASSESSMENT)
                    assert profile.provider is LlmProvider.OPENAI_COMPATIBLE
                    assert profile.is_tested
                    assert selection.provenance.policy == (
                        "global" if destination is None else "team"
                    )
                    assert (
                        profile.config_hash
                        == original["llm_connection_bindings"][0]["tested_config_hash"]
                    )
            await asyncio.to_thread(command.downgrade, config, "0017")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                await connection.run_sync(lambda sync: _assert_schema(sync, upgraded=False))
        finally:
            await engine.dispose()


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
@pytest.mark.parametrize("case", ["native", "long_credential", "long_model", "historical_model"])
async def test_provider_migration_roundtrip_and_refuses_lossy_downgrade(
    dialect: str, case: str, tmp_path: Path
) -> None:
    async with _database(dialect, tmp_path) as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0017")
        engine = create_async_engine(url, poolclass=sa.NullPool)
        try:
            async with engine.begin() as connection:
                original = await connection.run_sync(_seed_tested_binding)
            await asyncio.to_thread(command.upgrade, config, "0018")
            factory = async_sessionmaker(engine)
            cipher = FernetCipher("synthetic-local-migration-key-" * 2)
            plaintext = "s" * (16_384 if case == "long_credential" else 64)
            async with factory() as session:
                repository = SqlLlmProfileRepository(session)
                source = (await repository.list_all())[0]
                created = replace(
                    source,
                    id=uuid4(),
                    name="Synthetic new provider",
                    provider=LlmProvider.BEDROCK
                    if case == "native"
                    else LlmProvider.OPENAI_COMPATIBLE,
                    api_key_encrypted=cipher.encrypt(plaintext),
                    tested_at=None,
                    tested_revision=None,
                    tested_config_hash=None,
                    model=MODEL_ARN if case in {"native", "long_model"} else source.model,
                )
                await repository.add(created)
                await session.commit()
            async with factory() as session:
                repository = SqlLlmProfileRepository(session)
                saved = await repository.get(created.id)
                assert saved is not None and saved.provider is created.provider
                assert saved.model == created.model
                assert cipher.decrypt(saved.api_key_encrypted) == plaintext
                # Exercise repository save as well as insert with the long encrypted payload.
                saved.api_key_encrypted = cipher.encrypt(plaintext)
                await repository.save(saved)
                await session.commit()
            async with factory() as session:
                saved = await SqlLlmProfileRepository(session).get(created.id)
                assert saved is not None and cipher.decrypt(saved.api_key_encrypted) == plaintext
                if case == "long_credential":
                    assert len(saved.api_key_encrypted) > 2048
                if case == "historical_model":
                    version = await session.get(
                        ReportVersionRow, UUID(str(original["report_versions"][0]["id"]))
                    )
                    assert version is not None
                    version.model = MODEL_ARN
                    await session.commit()
            if case == "historical_model":
                async with factory() as session:
                    version = await session.get(
                        ReportVersionRow, UUID(str(original["report_versions"][0]["id"]))
                    )
                    assert version is not None and version.model == MODEL_ARN
            async with engine.connect() as connection:
                before_refusal = await connection.run_sync(_snapshot)
            match = {
                "native": "native provider",
                "long_credential": "encrypted credentials",
                "long_model": "model identifiers",
                "historical_model": "historical report",
            }[case]
            with pytest.raises(RuntimeError, match=match):
                await asyncio.to_thread(command.downgrade, config, "0017")
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                    == "0018"
                )
                await connection.run_sync(lambda sync: _assert_preserved(sync, before_refusal))
            async with factory() as session:
                await SqlLlmProfileRepository(session).delete(created.id)
                if case == "historical_model":
                    version = await session.get(
                        ReportVersionRow, UUID(str(original["report_versions"][0]["id"]))
                    )
                    assert version is not None
                    version.model = original["report_versions"][0]["model"]
                await session.commit()
            await asyncio.to_thread(command.downgrade, config, "0017")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                await connection.run_sync(lambda sync: _assert_schema(sync, upgraded=False))
        finally:
            await engine.dispose()

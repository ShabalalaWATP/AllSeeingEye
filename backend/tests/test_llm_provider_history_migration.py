"""Downgrade keeps immutable model provenance readable or refuses without writes."""

import asyncio
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.llm import SqlLlmProfileRepository
from ase.adapters.persistence.llm_bindings import SqlLlmBindingRepository
from ase.adapters.persistence.operational_models import ReportVersionRow
from ase.application.model_routing import ModelRouting
from ase.domain.llm import LlmProvider
from ase.domain.model_routing_records import routing_to_dict
from ase.infrastructure.migrations import alembic_config
from test_llm_connections_migration import _database
from test_llm_providers_migration import _assert_preserved, _seed_tested_binding, _snapshot


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
@pytest.mark.parametrize("history", ["legacy", "openai", "bedrock", "unreadable"])
async def test_provider_history_survives_or_prevents_downgrade(
    dialect: str, history: str, tmp_path: Path
) -> None:
    async with _database(dialect, tmp_path) as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0017")
        engine = create_async_engine(url, poolclass=sa.NullPool)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(_seed_tested_binding)
            await asyncio.to_thread(command.upgrade, config, "0018")
            async with async_sessionmaker(engine)() as session:
                router = ModelRouting(
                    SqlLlmProfileRepository(session), SqlLlmBindingRepository(session)
                )
                record = (await router.snapshot()).provenance
                if history == "bedrock":
                    # History remains after a native profile has gone: no live Bedrock profile
                    # or long model identifier can trigger the other downgrade guards.
                    record = replace(
                        record,
                        profiles=tuple(
                            replace(profile, provider=LlmProvider.BEDROCK)
                            for profile in record.profiles
                        ),
                    )
                routing = routing_to_dict(record)
                assert routing is not None
                if history == "legacy":
                    for profile in routing["profiles"]:
                        del profile["provider"]
                version = (await session.scalars(sa.select(ReportVersionRow))).one()
                version.analysis = {
                    "model_routing": "unreadable" if history == "unreadable" else routing
                }
                if history == "unreadable":
                    # Force the unsafe history onto the second bounded keyset page.
                    version.id = UUID(int=2**128 - 1)
                    values = {
                        column.name: getattr(version, column.name)
                        for column in ReportVersionRow.__table__.columns
                        if column.name not in {"id", "number", "analysis"}
                    }
                    session.add_all(
                        ReportVersionRow(
                            id=UUID(int=index), number=index + 1, analysis=None, **values
                        )
                        for index in range(1, 101)
                    )
                await session.commit()
            async with engine.connect() as connection:
                original = await connection.run_sync(_snapshot)
                # The snapshot must compare only the fields available after safe legacy downgrade.
                if history == "legacy":
                    for profile in original["llm_profiles"]:
                        del profile["provider"]
            if history == "legacy":
                await asyncio.to_thread(command.downgrade, config, "0017")
            else:
                with pytest.raises(RuntimeError, match="historical routing"):
                    await asyncio.to_thread(command.downgrade, config, "0017")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                assert await connection.scalar(
                    sa.text("SELECT version_num FROM alembic_version")
                ) == ("0017" if history == "legacy" else "0018")
        finally:
            await engine.dispose()

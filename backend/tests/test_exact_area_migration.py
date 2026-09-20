"""Additive exact-area migration preserves old rows and refuses lossy rollback."""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations

from ase.infrastructure.migrations import alembic_config


def test_full_sqlite_chain_preserves_existing_operational_rows(tmp_path):
    database = tmp_path / "exact-area-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0063")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        before = set(sa.inspect(engine).get_table_names())
        command.upgrade(config, "0064")
        assert set(sa.inspect(engine).get_table_names()) == before
        for table in ("aois", "indicators"):
            assert "research_area" in {row["name"] for row in sa.inspect(engine).get_columns(table)}
        command.downgrade(config, "0063")
        for table in ("aois", "indicators"):
            assert "research_area" not in {
                row["name"] for row in sa.inspect(engine).get_columns(table)
            }
    finally:
        engine.dispose()


def test_additive_migration_and_lossless_downgrade():
    path = Path(__file__).parents[1] / "alembic/versions/0064_exact_operational_areas.py"
    spec = importlib.util.spec_from_file_location("exact_area_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        for table in ("aois", "indicators"):
            sa.Table(table, sa.MetaData(), sa.Column("id", sa.Integer, primary_key=True)).create(
                connection
            )
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            assert "research_area" in {
                row["name"] for row in sa.inspect(connection).get_columns("aois")
            }
            module.downgrade()
            module.upgrade()
            table = sa.table("aois", sa.column("id"), sa.column("research_area", sa.JSON()))
            connection.execute(table.insert().values(id=1, research_area={"geometry": "retained"}))
            with pytest.raises(RuntimeError, match="explicitly"):
                module.downgrade()
            assert "research_area" in {
                row["name"] for row in sa.inspect(connection).get_columns("indicators")
            }
    engine.dispose()

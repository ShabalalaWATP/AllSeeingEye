"""Migration 0079 adds a nullable resume instant to alert rules and removes it losslessly."""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def _columns(engine: sa.Engine) -> set[str]:
    return {column["name"] for column in sa.inspect(engine).get_columns("indicators")}


def test_indicator_resume_migration_round_trip_on_sqlite(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "indicator-resume-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0078")
    engine = sa.create_engine(f"sqlite:///{database}")
    rule = uuid4().hex
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO indicators (id, name, description, countries, categories,"
                    " keywords, threshold, window_minutes, cooldown_minutes, severity_floor,"
                    " enabled, created_by, created_at, updated_at) VALUES (:id, 'Kharkiv', '',"
                    " '[]', '[]', '[]', 1, 60, 60, 0, 1, :owner, '2026-10-01', '2026-10-01')"
                ),
                {"id": rule, "owner": uuid4().hex},
            )
        assert "resumed_at" not in _columns(engine)
        command.upgrade(config, "0079")
        assert "resumed_at" in _columns(engine)
        with engine.begin() as connection:
            assert connection.execute(sa.text("SELECT resumed_at FROM indicators")).all() == [
                (None,)
            ]
            connection.execute(sa.text("UPDATE indicators SET resumed_at = '2026-10-01 12:00:00'"))
        command.downgrade(config, "0078")
        assert "resumed_at" not in _columns(engine)
        with engine.begin() as connection:
            assert connection.execute(sa.text("SELECT name FROM indicators")).all() == [
                ("Kharkiv",)
            ]
    finally:
        engine.dispose()

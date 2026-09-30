"""Downgrades must preserve frozen alert ratios after a rule changes or disappears."""

import sqlite3
from contextlib import closing

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def _ratio_database(tmp_path, mean, ratio):
    database = tmp_path / "ratio-history.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0070")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(connection, metadata.tables["users"], role="user")
            rule = _insert(
                connection, metadata.tables["indicators"], created_by=owner, baseline_ratio=3.0
            )
            _insert(
                connection,
                metadata.tables["alerts"],
                indicator_id=rule,
                created_by=owner,
                schedule_id=None,
                annotation_monitor_id=None,
                annotation_transition_id=None,
                baseline_mean=mean,
                baseline_ratio=ratio,
            )
    finally:
        engine.dispose()
    return config, database


def _snapshot(database):
    # Includes all rows, schema definitions and the Alembic revision.
    with closing(sqlite3.connect(database)) as connection:
        return tuple(connection.iterdump())


@pytest.mark.parametrize("rule_state", ["absolute", "deleted"])
@pytest.mark.parametrize("mean,ratio", [(2.0, None), (None, 3.0), (2.0, 3.0)])
def test_downgrade_refuses_frozen_alert_values_before_ddl(tmp_path, rule_state, mean, ratio):
    config, database = _ratio_database(tmp_path, mean, ratio)
    with closing(sqlite3.connect(database)) as connection, connection:
        # Both are supported application operations; neither rewrites fired alerts.
        if rule_state == "absolute":
            connection.execute("UPDATE indicators SET baseline_ratio=NULL")
        else:
            connection.execute("DELETE FROM indicators")
        assert connection.execute("SELECT baseline_mean,baseline_ratio FROM alerts").fetchone() == (
            mean,
            ratio,
        )
    before = _snapshot(database)
    with pytest.raises(RuntimeError, match="retained alert baseline"):
        command.downgrade(config, "0069")
    assert _snapshot(database) == before
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0070",)


def test_downgrade_still_refuses_configured_ratio_rule_before_ddl(tmp_path):
    config, database = _ratio_database(tmp_path, None, None)
    before = _snapshot(database)
    with pytest.raises(RuntimeError, match="ratio rules"):
        command.downgrade(config, "0069")
    assert _snapshot(database) == before


def test_downgrade_without_ratios_preserves_other_alert_fields(tmp_path):
    config, database = _ratio_database(tmp_path, None, None)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE indicators SET baseline_ratio=NULL")
        before = connection.execute("SELECT id,title,summary,count FROM alerts").fetchall()
    command.downgrade(config, "0069")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT id,title,summary,count FROM alerts").fetchall() == before
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0069",)
        assert not {"baseline_mean", "baseline_ratio"} & {
            row[1] for row in connection.execute("PRAGMA table_info(alerts)")
        }
        assert not {"baseline_days", "baseline_ratio"} & {
            row[1] for row in connection.execute("PRAGMA table_info(indicators)")
        }

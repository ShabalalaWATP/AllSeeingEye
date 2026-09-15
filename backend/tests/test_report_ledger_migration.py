"""0044 adds retained ledgers without rewriting report and claim rows."""

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_0044_additive_upgrade_and_retained_history_guard(tmp_path: Path) -> None:
    database = tmp_path / "forecast-ledger-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0043")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        meta = sa.MetaData()
        meta.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(
                connection, meta.tables["users"], email="forecast@example.com", role="user"
            )
            report = _insert(connection, meta.tables["reports"], created_by=owner)
            version = _insert(connection, meta.tables["report_versions"], report_id=report)
            before = dict(
                connection.execute(sa.select(meta.tables["report_versions"])).mappings().one()
            )
        command.upgrade(config, "0044")
        meta.clear()
        meta.reflect(engine)
        with engine.begin() as connection:
            after = dict(
                connection.execute(sa.select(meta.tables["report_versions"])).mappings().one()
            )
            assert after == before
            claim = _insert(
                connection,
                meta.tables["claims"],
                report_id=report,
                report_version_id=version,
                created_by=owner,
            )
            revision = _insert(connection, meta.tables["claim_revisions"], claim_id=claim)
            connection.execute(
                meta.tables["report_ledger_heads"]
                .insert()
                .values(
                    id=uuid4().hex,
                    kind="forecast",
                    report_id=report,
                    report_version_id=version,
                    claim_id=claim,
                    claim_revision_id=revision,
                    owner_id=owner,
                    latest_ordinal=1,
                    created_at=before["created_at"],
                )
            )
        with pytest.raises(RuntimeError, match="retained forecast"):
            command.downgrade(config, "0043")
        with engine.begin() as connection:
            connection.execute(meta.tables["report_ledger_heads"].delete())
        command.downgrade(config, "0043")
        assert "report_ledger_heads" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()

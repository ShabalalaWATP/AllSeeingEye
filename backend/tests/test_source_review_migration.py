"""Reviewer history migration is additive and refuses deletion of retained decisions."""

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_0043_preserves_old_versions_and_guards_retained_history(tmp_path: Path) -> None:
    database = tmp_path / "source-review-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0042")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(
                connection, metadata.tables["users"], email="review@example.com", role="user"
            )
            report = _insert(connection, metadata.tables["reports"], created_by=owner)
            _insert(
                connection,
                metadata.tables["report_versions"],
                report_id=report,
                body={"summary": "Historical report"},
                evidence=[{"id": "retained"}],
            )
            old = dict(
                connection.execute(sa.select(metadata.tables["report_versions"])).mappings().one()
            )
        command.upgrade(config, "0043")
        metadata.clear()
        metadata.reflect(engine)
        with engine.begin() as connection:
            saved = dict(
                connection.execute(sa.select(metadata.tables["report_versions"])).mappings().one()
            )
            assert saved == old
            connection.execute(
                metadata.tables["source_review_heads"]
                .insert()
                .values(key="a" * 64, owner_id=owner, kind="reliability", latest_id=uuid4().hex)
            )
        with pytest.raises(RuntimeError, match="retained source review"):
            command.downgrade(config, "0042")
        with engine.begin() as connection:
            connection.execute(metadata.tables["source_review_heads"].delete())
        command.downgrade(config, "0042")
        assert "source_review_heads" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()

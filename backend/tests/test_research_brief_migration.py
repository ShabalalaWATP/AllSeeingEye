"""Additive 0036 migration on a disposable populated SQLite database."""

from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command

from ase.adapters.persistence.research_briefs import _canonical_payload
from ase.infrastructure.migrations import alembic_config
from test_research_brief_persistence import _brief
from test_subscription_edition_migration import _seed


def test_brief_migration_preserves_legacy_jobs_and_schedules(tmp_path: Path) -> None:
    database = tmp_path / "r01-disposable.db"
    sync_url = f"sqlite:///{database}"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0034")
    engine, schedule_id, owner_id, _, _, jobs = _seed(sync_url)
    try:
        command.upgrade(config, "0035")
        command.upgrade(config, "0036")
        metadata = sa.MetaData()
        metadata.reflect(engine)
        schedules = metadata.tables["schedules"]
        report_jobs = metadata.tables["report_jobs"]
        revisions = metadata.tables["research_brief_revisions"]
        assert {"brief_id", "brief_revision"} <= set(schedules.c.keys())
        assert {"brief_id", "brief_revision"} <= set(report_jobs.c.keys())
        assert any(
            set(fk["constrained_columns"]) == {"brief_id", "brief_revision"}
            for fk in sa.inspect(engine).get_foreign_keys("schedules")
        )
        assert any(
            set(fk["constrained_columns"]) == {"brief_id", "brief_revision"}
            for fk in sa.inspect(engine).get_foreign_keys("report_jobs")
        )
        with engine.connect() as connection:
            schedule = (
                connection.execute(sa.select(schedules).where(schedules.c.id == schedule_id))
                .mappings()
                .one()
            )
            assert schedule["brief_id"] is None
            assert schedule["brief_revision"] is None
            retained_jobs = connection.execute(sa.select(report_jobs)).mappings().all()
            assert len(retained_jobs) == len(jobs)
            assert all(
                row["brief_id"] is None and row["brief_revision"] is None for row in retained_jobs
            )
            assert {row["status"] for row in retained_jobs} == {row["status"] for row in jobs}
        brief = _brief(owner_id=UUID(str(owner_id)))
        payload, digest, size = _canonical_payload(brief)
        identity = brief.identity
        with engine.begin() as connection:
            connection.execute(
                revisions.insert().values(
                    brief_id=identity.id.hex,
                    revision=identity.revision,
                    owner_id=identity.owner_id.hex,
                    team_id=None,
                    title=identity.title,
                    schema_version=identity.schema_version,
                    origin=identity.origin,
                    published=identity.published,
                    created_at=identity.created_at,
                    revised_at=identity.revised_at,
                    payload=payload,
                    payload_sha256=digest,
                    payload_bytes=size,
                )
            )
            connection.execute(
                schedules.update()
                .where(schedules.c.id == schedule_id)
                .values(brief_id=identity.id.hex, brief_revision=1)
            )
            connection.execute(
                report_jobs.update()
                .where(report_jobs.c.id == jobs[0]["id"])
                .values(brief_id=identity.id.hex, brief_revision=1)
            )
        with pytest.raises(RuntimeError, match="retained Research Brief"):
            command.downgrade(config, "0035")
        with engine.begin() as connection:
            connection.execute(
                schedules.update()
                .where(schedules.c.id == schedule_id)
                .values(brief_id=None, brief_revision=None)
            )
            connection.execute(
                report_jobs.update()
                .where(report_jobs.c.id == jobs[0]["id"])
                .values(brief_id=None, brief_revision=None)
            )
            connection.execute(revisions.delete())
        command.downgrade(config, "0035")
        assert "research_brief_revisions" not in sa.inspect(engine).get_table_names()
        assert "brief_id" not in {
            col["name"] for col in sa.inspect(engine).get_columns("schedules")
        }
        assert "brief_id" not in {
            col["name"] for col in sa.inspect(engine).get_columns("report_jobs")
        }
    finally:
        engine.dispose()

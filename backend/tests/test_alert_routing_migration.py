"""The additive routing migration leaves existing installations opted out."""

import asyncio

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_additive_routing_migration_and_downgrade(tmp_path):
    database = tmp_path / "routing-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    try:
        command.upgrade(config, "0071")
        engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
        with engine.connect() as connection:
            previous = set(sa.inspect(connection).get_table_names())
        command.upgrade(config, "0072")
        with engine.connect() as connection:
            tables = set(sa.inspect(connection).get_table_names())
            added = {
                "alert_webhook_destinations",
                "alert_notification_routes",
                "alert_notification_outbox",
            }
            assert tables - previous == added
            metadata = sa.MetaData()
            for table in added:
                migrated = sa.Table(table, metadata, autoload_with=connection)
                assert connection.scalar(sa.select(sa.func.count()).select_from(migrated)) == 0
            unique = sa.inspect(connection).get_unique_constraints("alert_notification_outbox")
            assert any(
                item["column_names"] == ["alert_id", "channel", "destination_ref"]
                for item in unique
            )
            columns = {
                item["name"]
                for item in sa.inspect(connection).get_columns("alert_webhook_destinations")
            }
            assert "url_encrypted" in columns and "url" not in columns
        command.downgrade(config, "0071")
        with engine.connect() as connection:
            assert set(sa.inspect(connection).get_table_names()) == previous
        engine.dispose()
    finally:
        asyncio.set_event_loop(asyncio.new_event_loop())

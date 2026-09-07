"""Read the frozen 0018 binding schema without depending on later ORM columns."""

from datetime import UTC
from uuid import UUID

import sqlalchemy as sa

from ase.domain.llm import LlmConnectionBinding


class LegacyBindingReader:
    def __init__(self, session):
        self.session = session

    async def list_all(self):
        connection = await self.session.connection()
        table = await connection.run_sync(
            lambda sync: sa.Table("llm_connection_bindings", sa.MetaData(), autoload_with=sync)
        )
        assert "user_id" not in table.c, "This reader tests the historical 0018 boundary only"
        rows = (await self.session.execute(sa.select(table).order_by(table.c.scope_key))).mappings()
        return [
            LlmConnectionBinding(
                team_id=UUID(str(row["team_id"])) if row["team_id"] else None,
                profile_id=UUID(str(row["profile_id"])),
                profile_revision=row["profile_revision"],
                tested_config_hash=row["tested_config_hash"],
                activated_at=row["activated_at"].replace(tzinfo=UTC)
                if row["activated_at"].tzinfo is None
                else row["activated_at"].astimezone(UTC),
                activated_by=UUID(str(row["activated_by"])),
                revision=row["revision"],
            )
            for row in rows
        ]

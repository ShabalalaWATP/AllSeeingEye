"""The saved conversation table has owner and size constraints."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from ase.adapters.persistence.assistant_history_models import AssistantConversationRow


def _migration():
    path = Path(__file__).parents[1] / "alembic/versions/0034_assistant_conversations.py"
    spec = importlib.util.spec_from_file_location("assistant_history_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_saved_chat_migration_constraints_and_retained_data_guard():
    module = _migration()
    assert module.revision == "0034" and module.down_revision == "0033"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            inspector = inspect(connection)
            assert "assistant_conversations" in inspector.get_table_names()
            checks = {
                item["name"] for item in inspector.get_check_constraints("assistant_conversations")
            }
            assert "ck_assistant_transcript_size" in checks
            assert "ck_assistant_turn_count" in checks
            now = datetime.now(UTC)
            connection.execute(
                AssistantConversationRow.__table__.insert().values(
                    id=uuid4(),
                    owner_id=uuid4(),
                    title="Example",
                    transcript='{"turns":[]}',
                    transcript_bytes=12,
                    turn_count=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            with pytest.raises(RuntimeError, match="saved conversations remain"):
                module.downgrade()
            connection.execute(AssistantConversationRow.__table__.delete())
            module.downgrade()
            assert "assistant_conversations" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()

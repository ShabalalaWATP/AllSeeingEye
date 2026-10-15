"""The operational CLI opens its selected database without creating or migrating schema."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from ase.adapters.persistence.models import PasswordTokenRow
from ase.cli_auth_retention import _run
from auth_retention_helpers import count, password, seed
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("dry_run,paused", [(True, False), (False, False), (False, True)])
async def test_cli_database_preview_apply_and_hold(race_container, dry_run, paused):
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    await seed(container, password(user, datetime.now(UTC) - timedelta(days=8)))
    settings = container.settings.model_copy(update={"auth_retention_paused": paused})
    result = await _run(settings, dry_run=dry_run)
    assert result.get("password_links", 0) == (not paused)
    assert await count(container, PasswordTokenRow) == (dry_run or paused)


async def test_cli_closes_database_after_transaction_failure(settings, monkeypatch):
    engine = Mock(dispose=AsyncMock())
    monkeypatch.setattr("ase.cli_auth_retention.create_engine", Mock(return_value=engine))
    monkeypatch.setattr("ase.cli_auth_retention.create_session_factory", Mock())
    monkeypatch.setattr(
        "ase.container.auth_retention.maintain_authentication",
        AsyncMock(side_effect=RuntimeError()),
    )
    with pytest.raises(RuntimeError):
        await _run(settings, dry_run=False)
    engine.dispose.assert_awaited_once()

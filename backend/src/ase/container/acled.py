"""ACLED OAuth refresh wiring: only built when the operator supplies a refresh token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ase.adapters.feeds.acled_http import AcledHttpClient
from ase.adapters.feeds.acled_tokens import AcledTokens
from ase.adapters.feeds.conflict_acled import SPEC
from ase.adapters.persistence.acled_credentials import SqlAcledCredentialStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from ase.application.ports import Clock
    from ase.application.ports.llm import SecretCipher
    from ase.infrastructure.settings import Settings


def build_acled_tokens(
    settings: Settings,
    sessions: async_sessionmaker[AsyncSession],
    cipher: SecretCipher,
    clock: Clock,
) -> AcledTokens | None:
    token = settings.acled_refresh_token
    if token is None or not token.get_secret_value().strip():
        return None
    if SPEC.id in settings.disabled_feed_ids:
        return None
    return AcledTokens(
        AcledHttpClient(settings.feeds_user_agent),
        clock,
        token,
        SqlAcledCredentialStore(sessions, clock),
        cipher,
    )

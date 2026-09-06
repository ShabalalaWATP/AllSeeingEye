"""Seed migrated legacy profiles for tests unrelated to connection draft/test/apply flows."""

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ase.container import Container
from ase.domain.llm import LlmProfile, LlmRole, key_hint


async def seed_legacy_profile(container: Container, settings: Mapping[str, Any]) -> LlmProfile:
    """Represent an already-enabled pre-migration profile, without bypassing an API gate."""
    now = container.clock.now()
    key = settings.get("api_key", "")
    profile = LlmProfile(
        id=uuid4(),
        name=settings["name"],
        base_url=settings["base_url"].rstrip("/"),
        model=settings["model"],
        api_key_encrypted=container.cipher.encrypt(key),
        api_key_hint=key_hint(key),
        roles=frozenset(LlmRole(role) for role in settings["roles"]),
        max_output_tokens=settings["max_output_tokens"],
        temperature=settings["temperature"],
        enabled=settings.get("enabled", True),
        created_at=now,
        updated_at=now,
    )
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.add(profile)
        await session.commit()
    return profile

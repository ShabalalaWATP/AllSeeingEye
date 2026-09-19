"""LLM profile and usage repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import LlmProfileRow, LlmUsageRow
from ase.domain.errors import Conflict, NotFound
from ase.domain.llm import LlmProfile, LlmProvider, LlmRole, LlmUsage, ReasoningEffort


def _profile_from_row(row: LlmProfileRow) -> LlmProfile:
    return LlmProfile(
        id=row.id,
        name=row.name,
        base_url=row.base_url,
        model=row.model,
        api_key_encrypted=row.api_key_encrypted,
        api_key_hint=row.api_key_hint,
        roles=frozenset(LlmRole(role) for role in row.roles),
        max_output_tokens=row.max_output_tokens,
        temperature=row.temperature,
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
        reasoning_effort=ReasoningEffort(row.reasoning_effort) if row.reasoning_effort else None,
        revision=row.revision,
        tested_at=row.tested_at,
        tested_revision=row.tested_revision,
        tested_config_hash=row.tested_config_hash,
        test_generation=row.test_generation,
        provider=LlmProvider(row.provider),
    )


def _apply_profile(row: LlmProfileRow, profile: LlmProfile) -> None:
    row.name = profile.name
    row.base_url = profile.base_url
    row.model = profile.model
    row.api_key_encrypted = profile.api_key_encrypted
    row.api_key_hint = profile.api_key_hint
    row.roles = sorted(role.value for role in profile.roles)
    row.max_output_tokens = profile.max_output_tokens
    row.temperature = profile.temperature
    row.enabled = profile.enabled
    row.created_at = profile.created_at
    row.updated_at = profile.updated_at
    row.reasoning_effort = profile.reasoning_effort
    row.revision = profile.revision
    row.tested_at = profile.tested_at
    row.tested_revision = profile.tested_revision
    row.tested_config_hash = profile.tested_config_hash
    row.test_generation = profile.test_generation
    row.provider = profile.provider.value


class SqlLlmProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, profile_id: UUID) -> LlmProfile | None:
        row = await self._session.get(LlmProfileRow, profile_id, populate_existing=True)
        return _profile_from_row(row) if row else None

    async def list_all(self) -> list[LlmProfile]:
        rows = await self._session.scalars(select(LlmProfileRow).order_by(LlmProfileRow.created_at))
        return [_profile_from_row(row) for row in rows]

    async def add(self, profile: LlmProfile) -> None:
        row = LlmProfileRow(id=profile.id)
        _apply_profile(row, profile)
        self._session.add(row)
        await self._flush_profile()

    async def save(self, profile: LlmProfile) -> None:
        row = await self._session.get(LlmProfileRow, profile.id)
        if row is None:
            raise NotFound()
        _apply_profile(row, profile)
        await self._flush_profile()

    async def _flush_profile(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Translate only this unique index (SQLite and PostgreSQL), including
            # concurrent creates. The request transaction still rolls back normally.
            detail = str(exc.orig).lower()
            if (
                "unique constraint failed: llm_profiles.name" in detail
                or 'duplicate key value violates unique constraint "ix_llm_profiles_name"' in detail
            ):
                raise Conflict(
                    "A connection with this name already exists. Choose a different name.",
                    fields={"name": "Choose a different connection name."},
                ) from None
            raise

    async def delete(self, profile_id: UUID) -> None:
        await self._session.execute(delete(LlmProfileRow).where(LlmProfileRow.id == profile_id))
        await self._session.flush()


class SqlLlmUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, usage: LlmUsage) -> None:
        row = LlmUsageRow(
            at=usage.at,
            profile_id=usage.profile_id,
            user_id=usage.user_id,
            purpose=usage.purpose,
            ok=usage.ok,
            latency_ms=usage.latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            error=usage.error,
        )
        self._session.add(row)
        await self._session.flush()
        usage.id = row.id

    async def list_recent(self, limit: int) -> list[LlmUsage]:
        rows = await self._session.scalars(
            select(LlmUsageRow).order_by(LlmUsageRow.id.desc()).limit(limit)
        )
        return [
            LlmUsage(
                id=row.id,
                at=row.at,
                profile_id=row.profile_id,
                user_id=row.user_id,
                purpose=row.purpose,
                ok=row.ok,
                latency_ms=row.latency_ms,
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                error=row.error,
            )
            for row in rows
        ]

"""LLM profile administration: keys encrypted at rest, never returned, tested on demand."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.embeddings import EmbeddingGateway
from ase.application.ports.llm import (
    LlmGateway,
    LlmGatewayError,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import EncryptionUnavailable, NotFound
from ase.domain.llm import (
    LlmMessage,
    LlmProfile,
    LlmRequest,
    LlmRole,
    LlmUsage,
    key_hint,
    normalise_base_url,
)
from ase.domain.report_search import checked_vector
from ase.domain.users import User

TEST_PROMPT = 'Reply with exactly this JSON object and nothing else: {"ok": true}'
TEST_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


@dataclass(frozen=True, slots=True)
class ProfileInput:
    name: str
    base_url: str
    model: str
    roles: frozenset[LlmRole]
    max_output_tokens: int
    temperature: float
    enabled: bool
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class TestOutcome:
    ok: bool
    latency_ms: float
    model: str | None = None
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ListLlmProfilesUseCase:
    def __init__(self, profiles: LlmProfileRepository) -> None:
        self._profiles = profiles

    async def execute(self, actor: User) -> list[LlmProfile]:
        require_admin(actor)
        return await self._profiles.list_all()


class CreateLlmProfileUseCase:
    def __init__(
        self,
        profiles: LlmProfileRepository,
        cipher: SecretCipher,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._profiles = profiles
        self._cipher = cipher
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(self, actor: User, data: ProfileInput, context: RequestContext) -> LlmProfile:
        require_admin(actor)
        if not self._cipher.available:
            raise EncryptionUnavailable()
        api_key = data.api_key or ""
        now = self._clock.now()
        profile = LlmProfile(
            id=uuid4(),
            name=data.name.strip(),
            base_url=normalise_base_url(data.base_url),
            model=data.model.strip(),
            api_key_encrypted=self._cipher.encrypt(api_key),
            api_key_hint=key_hint(api_key) if api_key else "",
            roles=data.roles,
            max_output_tokens=data.max_output_tokens,
            temperature=data.temperature,
            enabled=data.enabled,
            created_at=now,
            updated_at=now,
        )
        await self._profiles.add(profile)
        await self._auditor.record(
            AuditAction.LLM_PROFILE_CREATED,
            actor=actor.id,
            subject=profile.name,
            ip=context.ip,
            details={"model": profile.model, "base_url": profile.base_url},
        )
        await self._uow.commit()
        return profile


class UpdateLlmProfileUseCase:
    def __init__(
        self,
        profiles: LlmProfileRepository,
        cipher: SecretCipher,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._profiles = profiles
        self._cipher = cipher
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, actor: User, profile_id: UUID, data: ProfileInput, context: RequestContext
    ) -> LlmProfile:
        require_admin(actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        profile.name = data.name.strip()
        profile.base_url = normalise_base_url(data.base_url)
        profile.model = data.model.strip()
        profile.roles = data.roles
        profile.max_output_tokens = data.max_output_tokens
        profile.temperature = data.temperature
        profile.enabled = data.enabled
        changed_key = False
        if data.api_key:
            if not self._cipher.available:
                raise EncryptionUnavailable()
            profile.api_key_encrypted = self._cipher.encrypt(data.api_key)
            profile.api_key_hint = key_hint(data.api_key)
            changed_key = True
        profile.updated_at = self._clock.now()
        await self._profiles.save(profile)
        await self._auditor.record(
            AuditAction.LLM_PROFILE_UPDATED,
            actor=actor.id,
            subject=profile.name,
            ip=context.ip,
            details={
                "model": profile.model,
                "enabled": profile.enabled,
                "key_changed": changed_key,
            },
        )
        await self._uow.commit()
        return profile


class DeleteLlmProfileUseCase:
    def __init__(self, profiles: LlmProfileRepository, auditor: Auditor, uow: UnitOfWork) -> None:
        self._profiles = profiles
        self._auditor = auditor
        self._uow = uow

    async def execute(self, actor: User, profile_id: UUID, context: RequestContext) -> None:
        require_admin(actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        await self._profiles.delete(profile_id)
        await self._auditor.record(
            AuditAction.LLM_PROFILE_DELETED, actor=actor.id, subject=profile.name, ip=context.ip
        )
        await self._uow.commit()


class TestLlmProfileUseCase:
    """Probe the configured capability, using embeddings for embeddings-only profiles."""

    def __init__(
        self,
        profiles: LlmProfileRepository,
        usage: LlmUsageRepository,
        cipher: SecretCipher,
        gateway: LlmGateway,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        *,
        embeddings: EmbeddingGateway | None = None,
    ) -> None:
        self._profiles = profiles
        self._usage = usage
        self._cipher = cipher
        self._gateway = gateway
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._embeddings = embeddings

    async def execute(self, actor: User, profile_id: UUID, context: RequestContext) -> TestOutcome:
        require_admin(actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        if not self._cipher.available:
            raise EncryptionUnavailable()
        request = LlmRequest(
            messages=(LlmMessage("user", TEST_PROMPT),),
            max_output_tokens=min(profile.max_output_tokens, 200),
            temperature=0.0,
            json_schema=TEST_SCHEMA,
            schema_name="connection_test",
        )
        embeddings_only = profile.roles == frozenset({LlmRole.EMBEDDINGS})
        outcome = (
            await self._call_embeddings(profile)
            if embeddings_only
            else await self._call(profile, request)
        )
        await self._usage.add(
            LlmUsage(
                at=self._clock.now(),
                profile_id=profile.id,
                user_id=actor.id,
                purpose="embeddings" if embeddings_only else "connection_test",
                ok=outcome.ok,
                latency_ms=outcome.latency_ms,
                error=outcome.error,
                prompt_tokens=outcome.prompt_tokens,
                completion_tokens=outcome.completion_tokens,
            )
        )
        await self._auditor.record(
            AuditAction.LLM_PROFILE_TESTED,
            actor=actor.id,
            subject=profile.name,
            ip=context.ip,
            details={"ok": outcome.ok, "error": outcome.error},
        )
        await self._uow.commit()
        return outcome

    async def _call_embeddings(self, profile: LlmProfile) -> TestOutcome:
        if self._embeddings is None:
            return TestOutcome(
                ok=False, latency_ms=0, error="The embeddings gateway is unavailable."
            )
        try:
            api_key = self._cipher.decrypt(profile.api_key_encrypted)
            result = await self._embeddings.embed(
                profile.base_url, api_key, profile.model, ("Semantic search connection test.",)
            )
            if len(result.vectors) != 1:
                raise ValueError("Expected one embedding.")
            checked_vector(result.vectors[0])
        except Exception:
            return TestOutcome(
                ok=False,
                latency_ms=0,
                error="The embeddings connection test failed. Check the model profile.",
            )
        return TestOutcome(
            ok=True,
            latency_ms=result.latency_ms,
            model=profile.model,
            prompt_tokens=result.prompt_tokens,
        )

    async def _call(self, profile: LlmProfile, request: LlmRequest) -> TestOutcome:
        try:
            api_key = self._cipher.decrypt(profile.api_key_encrypted)
            result = await self._gateway.complete(profile.base_url, api_key, profile.model, request)
        except LlmGatewayError as exc:
            return TestOutcome(ok=False, latency_ms=0.0, error=str(exc))
        except Exception as exc:  # the stored key may be unreadable after a key rotation
            return TestOutcome(ok=False, latency_ms=0.0, error=str(exc))
        try:
            parsed = json.loads(result.content)
        except (ValueError, RecursionError):
            return TestOutcome(
                ok=False, latency_ms=result.latency_ms, model=result.model,
                error="The model did not answer with JSON.",
            )  # fmt: skip
        if parsed != {"ok": True}:
            return TestOutcome(
                ok=False, latency_ms=result.latency_ms, model=result.model,
                error="The model answered, but not with the expected object.",
            )  # fmt: skip
        return TestOutcome(
            ok=True,
            latency_ms=result.latency_ms,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )


class ListLlmUsageUseCase:
    def __init__(self, usage: LlmUsageRepository) -> None:
        self._usage = usage

    async def execute(self, actor: User, limit: int) -> list[LlmUsage]:
        require_admin(actor)
        return await self._usage.list_recent(limit)

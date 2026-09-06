"""LLM profile administration: keys encrypted at rest, never returned, tested on demand."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from ase.application.access import AccessPolicy
from ase.application.admin.llm_testing import SessionCheck
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.llm import (
    LlmBindingRepository,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.domain.audit import AuditAction
from ase.domain.bedrock import normalise_bedrock_base_url
from ase.domain.errors import EncryptionUnavailable, InvalidRequest, NotFound
from ase.domain.llm import (
    MAX_API_KEY_LENGTH,
    MAX_MODEL_ID_LENGTH,
    TEXT_ROLES,
    LlmProfile,
    LlmProvider,
    LlmRole,
    LlmUsage,
    ReasoningEffort,
    key_hint,
    normalise_base_url,
)
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class ProfileInput:
    name: str
    base_url: str
    model: str
    roles: frozenset[LlmRole]
    max_output_tokens: int
    temperature: float
    enabled: bool
    api_key: str | None = field(default=None, repr=False)
    reasoning_effort: ReasoningEffort | None = None
    provider: LlmProvider = LlmProvider.OPENAI_COMPATIBLE

    def __post_init__(self) -> None:
        if (
            not self.name.strip()
            or len(self.name) > 80
            or not self.model.strip()
            or len(self.model)
            > (MAX_MODEL_ID_LENGTH if self.provider is LlmProvider.BEDROCK else 120)
            or not 64 <= self.max_output_tokens <= 32_000
            or not math.isfinite(self.temperature)
            or not 0 <= self.temperature <= 2
            or any(role not in LlmRole for role in self.roles)
            or (self.reasoning_effort is not None and self.reasoning_effort not in ReasoningEffort)
            or (self.api_key is not None and len(self.api_key) > MAX_API_KEY_LENGTH)
            or not isinstance(self.provider, LlmProvider)
        ):
            raise InvalidRequest("The model profile settings are invalid.")
        try:
            if self.provider is LlmProvider.BEDROCK:
                normalise_bedrock_base_url(self.base_url)
                if LlmRole.EMBEDDINGS in self.roles or self.reasoning_effort is not None:
                    raise InvalidRequest(
                        "Native Bedrock profiles support text roles without a reasoning setting."
                    )
                if self.temperature > 1:
                    raise InvalidRequest("Native Bedrock temperature must be between zero and one.")
            else:
                normalise_base_url(self.base_url)
        except ValueError as exc:
            raise InvalidRequest("The model endpoint address is invalid.") from exc


class ListLlmProfilesUseCase:
    def __init__(self, profiles: LlmProfileRepository, access: AccessPolicy) -> None:
        self._profiles = profiles
        self._access = access

    async def execute(self, actor: User) -> list[LlmProfile]:
        require_admin((await self._access.context(actor)).actor)
        return await self._profiles.list_all()


class CreateLlmProfileUseCase:
    def __init__(
        self,
        profiles: LlmProfileRepository,
        cipher: SecretCipher,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
        bindings: LlmBindingRepository,
    ) -> None:
        self._profiles = profiles
        self._access = access
        self._cipher = cipher
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._bindings = bindings

    async def execute(
        self,
        actor: User,
        data: ProfileInput,
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> LlmProfile:
        require_admin((await self._access.context(actor, for_update=True)).actor)
        if not self._cipher.available:
            raise EncryptionUnavailable()
        if data.provider is LlmProvider.BEDROCK and not data.api_key:
            raise InvalidRequest("Native Bedrock requires a bearer API key.")
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
            enabled=data.enabled and data.roles == frozenset({LlmRole.EMBEDDINGS}),
            created_at=now,
            updated_at=now,
            reasoning_effort=data.reasoning_effort,
            provider=data.provider,
        )
        if before_save is not None:
            await before_save()
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
        access: AccessPolicy,
        bindings: LlmBindingRepository,
    ) -> None:
        self._profiles = profiles
        self._access = access
        self._cipher = cipher
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._bindings = bindings

    async def execute(
        self,
        actor: User,
        profile_id: UUID,
        data: ProfileInput,
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> LlmProfile:
        require_admin((await self._access.context(actor, for_update=True)).actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        if await self._bindings.is_bound(profile_id):
            raise InvalidRequest(
                "An active connection cannot be edited. Create a replacement profile."
            )
        await _protect_legacy_profile(profile, self._bindings)
        destination = normalise_base_url(data.base_url)
        if not data.api_key and (
            profile.provider != data.provider
            or (profile.api_key_hint and destination != profile.base_url)
        ):
            raise InvalidRequest("Supply a new API key when changing the credential destination.")
        if data.provider is LlmProvider.BEDROCK and not data.api_key and not profile.api_key_hint:
            raise InvalidRequest("Native Bedrock requires a bearer API key.")
        profile.name = data.name.strip()
        profile.base_url = normalise_base_url(data.base_url)
        profile.model = data.model.strip()
        profile.roles = data.roles
        profile.max_output_tokens = data.max_output_tokens
        profile.temperature = data.temperature
        profile.enabled = data.enabled and data.roles == frozenset({LlmRole.EMBEDDINGS})
        profile.reasoning_effort = data.reasoning_effort
        profile.provider = data.provider
        profile.revision += 1
        profile.tested_at = None
        profile.tested_revision = None
        profile.tested_config_hash = None
        changed_key = False
        if data.api_key:
            if not self._cipher.available:
                raise EncryptionUnavailable()
            profile.api_key_encrypted = self._cipher.encrypt(data.api_key)
            profile.api_key_hint = key_hint(data.api_key)
            changed_key = True
        profile.updated_at = self._clock.now()
        if before_save is not None:
            await before_save()
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
    def __init__(
        self,
        profiles: LlmProfileRepository,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
        bindings: LlmBindingRepository,
    ) -> None:
        self._profiles = profiles
        self._access = access
        self._auditor = auditor
        self._uow = uow
        self._bindings = bindings

    async def execute(
        self,
        actor: User,
        profile_id: UUID,
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> None:
        require_admin((await self._access.context(actor, for_update=True)).actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        if await self._bindings.is_bound(profile_id):
            raise InvalidRequest(
                "An active connection cannot be deleted. Apply a replacement first."
            )
        await _protect_legacy_profile(profile, self._bindings)
        if before_save is not None:
            await before_save()
        await self._profiles.delete(profile_id)
        await self._auditor.record(
            AuditAction.LLM_PROFILE_DELETED, actor=actor.id, subject=profile.name, ip=context.ip
        )
        await self._uow.commit()


class ListLlmUsageUseCase:
    def __init__(self, usage: LlmUsageRepository, access: AccessPolicy) -> None:
        self._usage = usage
        self._access = access

    async def execute(self, actor: User, limit: int) -> list[LlmUsage]:
        require_admin((await self._access.context(actor)).actor)
        return await self._usage.list_recent(limit)


async def _protect_legacy_profile(profile: LlmProfile, bindings: LlmBindingRepository) -> None:
    if profile.enabled and profile.roles & TEXT_ROLES and await bindings.get(None) is None:
        raise InvalidRequest(
            "Legacy text configuration is in use. Apply a tested global replacement first."
        )

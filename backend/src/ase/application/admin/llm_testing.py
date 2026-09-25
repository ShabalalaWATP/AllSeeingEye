"""On-demand synthetic model probes and saved-profile discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.admin.model_catalogue import model_catalogue
from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceEmbeddingGateway, AllowanceLlmGateway
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.embeddings import EmbeddingGateway
from ase.application.ports.llm import (
    LlmGateway,
    LlmGatewayError,
    LlmModelDiscovery,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.application.ports.session import SessionCheck
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution
from ase.domain.audit import AuditAction
from ase.domain.errors import EncryptionUnavailable, InvalidRequest, NotFound
from ase.domain.llm import LlmMessage, LlmProfile, LlmProvider, LlmRequest, LlmRole, LlmUsage
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
class TestOutcome:
    ok: bool
    latency_ms: float
    model: str | None = None
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    revision: int | None = None
    tested_at: datetime | None = None
    tested_config_hash: str | None = None


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
        access: AccessPolicy,
        ai_usage: AiUsageAccounting | None = None,
    ) -> None:
        self._ai_usage = ai_usage
        self._profiles = profiles
        self._usage = usage
        self._cipher = cipher
        self._gateway = gateway
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._embeddings = embeddings
        self._access = access

    async def execute(
        self,
        actor: User,
        profile_id: UUID,
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> TestOutcome:
        require_admin((await self._access.context(actor, for_update=True)).actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        if not self._cipher.available:
            raise EncryptionUnavailable()
        request = LlmRequest(
            messages=(LlmMessage("user", TEST_PROMPT),),
            max_output_tokens=profile.max_output_tokens,
            temperature=profile.temperature,
            reasoning_effort=profile.reasoning_effort,
            provider=profile.provider,
            json_schema=TEST_SCHEMA,
            schema_name="connection_test",
        )
        fingerprint = profile.config_hash
        if before_save is not None:
            await before_save()
        # A durable generation orders concurrent probes across processes. An older success
        # must never replace a newer failure. Cancellation leaves a draft requiring retest.
        profile.test_generation += 1
        generation = profile.test_generation
        profile.tested_at = None
        profile.tested_revision = None
        profile.tested_config_hash = None
        await self._profiles.save(profile)
        await self._auditor.record(
            AuditAction.LLM_PROFILE_TEST_STARTED,
            actor=actor.id,
            subject=str(profile.id),
            ip=context.ip,
            details={"revision": profile.revision, "generation": generation},
        )
        await self._uow.commit()  # Never hold database locks across model work.
        embeddings_only = profile.roles == frozenset({LlmRole.EMBEDDINGS})
        outcome = (
            await self._call_embeddings(profile, actor.id)
            if embeddings_only
            else await self._call(profile, request, actor.id)
        )
        require_admin((await self._access.context(actor, for_update=True)).actor)
        current = await self._profiles.get(profile_id)
        if current is None:
            raise NotFound()
        if current.config_hash != fingerprint:
            raise InvalidRequest(
                "The profile changed during the test; test the saved revision again."
            )
        if current.test_generation != generation:
            raise InvalidRequest("A newer connection test superseded this result.")
        if before_save is not None:
            await before_save()
        # Existing bindings retain their own proof; failed probes block new activations.
        if outcome.ok:
            current.tested_at = self._clock.now()
            current.tested_revision = current.revision
            current.tested_config_hash = fingerprint
            outcome = replace(
                outcome,
                revision=current.revision,
                tested_at=current.tested_at,
                tested_config_hash=fingerprint,
            )
        else:
            current.tested_at = None
            current.tested_revision = None
            current.tested_config_hash = None
        await self._profiles.save(current)
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

    async def _call_embeddings(self, profile: LlmProfile, actor_id: UUID) -> TestOutcome:
        if self._embeddings is None:
            return TestOutcome(
                ok=False, latency_ms=0, error="The embeddings gateway is unavailable."
            )
        embeddings: EmbeddingGateway = self._embeddings
        if self._ai_usage is not None:
            embeddings = AllowanceEmbeddingGateway(
                embeddings,
                self._ai_usage,
                attribution=AiAttribution.actor(actor_id),
                profile_id=profile.id,
                purpose="connection_test:embeddings",
            )
        try:
            api_key = self._cipher.decrypt(profile.api_key_encrypted)
            result = await embeddings.embed(
                profile.base_url, api_key, profile.model, ("Semantic search connection test.",)
            )
            if len(result.vectors) != 1:
                raise ValueError("Expected one embedding.")
            checked_vector(result.vectors[0])
        except AiAllowanceExceeded:
            raise
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

    async def _call(self, profile: LlmProfile, request: LlmRequest, actor_id: UUID) -> TestOutcome:
        gateway: LlmGateway = self._gateway
        if self._ai_usage is not None:
            # Connection tests are charged to the administrator who runs them.
            gateway = AllowanceLlmGateway(
                gateway,
                self._ai_usage,
                attribution=AiAttribution.actor(actor_id),
                profile_id=profile.id,
                purpose_prefix="admin",
                strict=False,
            )
        try:
            api_key = self._cipher.decrypt(profile.api_key_encrypted)
            result = await gateway.complete(profile.base_url, api_key, profile.model, request)
        except AiAllowanceExceeded:
            raise
        except LlmGatewayError as exc:
            return TestOutcome(ok=False, latency_ms=0.0, error=str(exc))
        except Exception:  # Never expose unexpected provider/cipher exception text.
            return TestOutcome(
                ok=False,
                latency_ms=0.0,
                error="The connection test failed. Check the model profile and encryption key.",
            )
        try:
            parsed = json.loads(result.content)
        except (ValueError, RecursionError):
            return TestOutcome(
                ok=False, latency_ms=result.latency_ms, model=profile.model,
                error="The model did not answer with JSON.",
            )  # fmt: skip
        if not isinstance(parsed, dict) or set(parsed) != {"ok"} or parsed["ok"] is not True:
            return TestOutcome(
                ok=False, latency_ms=result.latency_ms, model=profile.model,
                error="The model answered, but not with the expected object.",
            )  # fmt: skip
        return TestOutcome(
            ok=True,
            latency_ms=result.latency_ms,
            model=profile.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )


class DiscoverLlmModelsUseCase:
    """Read model identifiers using one saved credential, rechecking after network work."""

    def __init__(
        self,
        profiles: LlmProfileRepository,
        cipher: SecretCipher,
        discovery: LlmModelDiscovery,
        access: AccessPolicy,
        uow: UnitOfWork,
    ) -> None:
        self._profiles, self._cipher, self._discovery = profiles, cipher, discovery
        self._access, self._uow = access, uow

    async def execute(
        self, actor: User, profile_id: UUID, *, before_return: SessionCheck | None = None
    ) -> tuple[str, ...]:
        require_admin((await self._access.context(actor)).actor)
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFound()
        if profile.provider is LlmProvider.BEDROCK:
            raise InvalidRequest(
                "Native Bedrock model discovery is unavailable. "
                "Enter a model or inference profile ID manually."
            )
        if not self._cipher.available:
            raise EncryptionUnavailable()
        fingerprint = profile.config_hash
        await self._uow.rollback()
        try:
            models = await self._discovery.list_models(
                profile.base_url, self._cipher.decrypt(profile.api_key_encrypted)
            )
        except Exception:
            models = None
        require_admin((await self._access.context(actor)).actor)
        current = await self._profiles.get(profile_id)
        if current is None or current.config_hash != fingerprint:
            raise InvalidRequest("The profile changed during discovery. Load models again.")
        if before_return is not None:
            await before_return()
        if models is None:
            raise InvalidRequest("Could not list models. Check the saved connection settings.")
        return model_catalogue(models)

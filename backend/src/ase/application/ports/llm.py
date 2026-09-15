"""Ports for language-model profiles: storage, secret handling and the model call itself."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.llm import LlmConnectionBinding, LlmProfile, LlmRequest, LlmResult, LlmUsage


class LlmBindingRepository(Protocol):
    async def next_revision(self) -> int: ...
    async def get(
        self, team_id: UUID | None, *, user_id: UUID | None = None
    ) -> LlmConnectionBinding | None: ...
    async def list_all(self) -> list[LlmConnectionBinding]: ...
    async def save(self, binding: LlmConnectionBinding) -> None: ...
    async def delete(self, team_id: UUID | None, *, user_id: UUID | None = None) -> None: ...
    async def is_bound(self, profile_id: UUID) -> bool: ...


class LlmModelDiscovery(Protocol):
    async def list_models(self, base_url: str, api_key: str) -> tuple[str, ...]: ...


class LlmProfileRepository(Protocol):
    async def get(self, profile_id: UUID) -> LlmProfile | None: ...
    async def list_all(self) -> list[LlmProfile]: ...
    async def add(self, profile: LlmProfile) -> None: ...
    async def save(self, profile: LlmProfile) -> None: ...
    async def delete(self, profile_id: UUID) -> None: ...


class LlmUsageRepository(Protocol):
    async def add(self, usage: LlmUsage) -> None: ...
    async def list_recent(self, limit: int) -> list[LlmUsage]: ...


class SecretCipher(Protocol):
    @property
    def available(self) -> bool:
        """False when no encryption key is configured; secrets cannot be stored then."""
        ...

    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...


class LlmGatewayError(Exception):
    """The model endpoint could not be used; the message never contains the key."""


class LlmGatewayTimeout(LlmGatewayError):
    """The request was sent but no answer arrived in time; the provider may still bill it."""


class LlmTokenBudgetExhausted(LlmGatewayError):
    """An explicit output limit, not a transient failure; do not repeat the same budget.

    Adapters may attach validated accounting metadata, never partial model output.
    """

    def __init__(
        self,
        *,
        model: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        super().__init__(
            "The model exhausted its completion token budget before producing a complete answer."
        )
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class LlmGateway(Protocol):
    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult: ...

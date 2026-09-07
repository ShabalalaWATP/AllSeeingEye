"""Discover model IDs from unsaved connection settings without persisting credentials."""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from ase.application.admin.model_catalogue import model_catalogue
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.policy import require_admin
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.llm import LlmModelDiscovery, LlmProfileRepository, SecretCipher
from ase.domain.errors import EncryptionUnavailable, InvalidRequest, NotFound, Unauthenticated
from ase.domain.llm import MAX_API_KEY_LENGTH, LlmProvider, normalise_base_url

DISCOVERY_TIMEOUT_SECONDS = 20


@dataclass(frozen=True, slots=True)
class DiscoveryInput:
    base_url: str
    api_key: str | None = field(default=None, repr=False)
    profile_id: UUID | None = None

    def __post_init__(self) -> None:
        try:
            endpoint = normalise_base_url(self.base_url)
        except (TypeError, ValueError) as exc:
            raise InvalidRequest("The model endpoint address is invalid.") from exc
        if len(endpoint) > 512 or (
            self.api_key is not None
            and (
                len(self.api_key) > MAX_API_KEY_LENGTH
                or any(ord(char) < 32 or ord(char) == 127 for char in self.api_key)
            )
        ):
            raise InvalidRequest("The connection settings are invalid.")
        object.__setattr__(self, "base_url", endpoint)


class DiscoverDraftModels:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        profiles: LlmProfileRepository,
        cipher: SecretCipher,
        discovery: LlmModelDiscovery,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.profiles = users, refresh, profiles
        self.cipher, self.discovery, self.clock, self.uow = cipher, discovery, clock, uow

    async def _guard(self, claims: AccessClaims) -> None:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        require_admin(await validate_current_session(claims, self.users, self.refresh, self.clock))

    async def execute(self, claims: AccessClaims, data: DiscoveryInput) -> tuple[str, ...]:
        await self._guard(claims)
        profile = await self.profiles.get(data.profile_id) if data.profile_id else None
        if data.profile_id and profile is None:
            raise NotFound()
        fingerprint = profile.config_hash if profile else None
        key = data.api_key or ""
        if not key and profile is not None:
            if (
                profile.provider is not LlmProvider.OPENAI_COMPATIBLE
                or normalise_base_url(profile.base_url) != data.base_url
            ):
                raise InvalidRequest("Enter a new key when changing the endpoint or provider.")
            if not self.cipher.available:
                raise EncryptionUnavailable()
            try:
                key = self.cipher.decrypt(profile.api_key_encrypted)
            except Exception:
                raise InvalidRequest("The saved credential could not be read.") from None
        # Discard the transaction and release administrative locks before outbound I/O.
        await self.uow.rollback()
        try:
            async with asyncio.timeout(DISCOVERY_TIMEOUT_SECONDS):
                models = await self.discovery.list_models(data.base_url, key)
        except Exception:
            models = None
        finally:
            key = ""
        await self.uow.rollback()
        await self._guard(claims)
        if data.profile_id:
            current = await self.profiles.get(data.profile_id)
            if current is None or current.config_hash != fingerprint:
                raise InvalidRequest("The profile changed during discovery. Load models again.")
        await self.uow.commit()
        if claims.expires_at <= self.clock.now():
            raise Unauthenticated("The session has ended. Sign in again.")
        if models is None:
            raise InvalidRequest("Could not list models. Check the endpoint and credential.")
        return model_catalogue(models)

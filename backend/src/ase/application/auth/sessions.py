"""Creates refresh-token families and access tokens for login and refresh."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.dto import AuthSession, RequestContext
from ase.application.ports import AccessTokenIssuer, Clock, RefreshTokenRepository, TokenGenerator
from ase.domain.tokens import RefreshToken
from ase.domain.users import User


class SessionFactory:
    def __init__(
        self,
        refresh_tokens: RefreshTokenRepository,
        issuer: AccessTokenIssuer,
        generator: TokenGenerator,
        clock: Clock,
        refresh_ttl: timedelta,
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._issuer = issuer
        self._generator = generator
        self._clock = clock
        self._refresh_ttl = refresh_ttl

    async def start(
        self,
        user: User,
        context: RequestContext,
        *,
        family_id: UUID | None = None,
        parent_id: UUID | None = None,
    ) -> AuthSession:
        now = self._clock.now()
        secret = self._generator.new_secret()
        token = RefreshToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=self._generator.hash(secret),
            family_id=family_id or uuid4(),
            parent_id=parent_id,
            issued_at=now,
            expires_at=now + self._refresh_ttl,
            revoked_at=None,
            ip=context.ip,
            user_agent=context.user_agent,
        )
        await self._refresh_tokens.add(token)
        return AuthSession(
            access=self._issuer.issue(user, token.family_id),
            refresh_secret=secret,
            csrf_token=self._generator.new_secret(),
            user=user,
        )

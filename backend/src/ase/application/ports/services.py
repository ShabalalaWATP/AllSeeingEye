"""Service ports: hashing, tokens, time, rate limiting, links and email."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.application.dto import AccessClaims, IssuedAccessToken
from ase.domain.tokens import TokenPurpose
from ase.domain.users import User


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...


class AccessTokenIssuer(Protocol):
    def issue(self, user: User, family_id: UUID) -> IssuedAccessToken: ...
    def verify(self, token: str) -> AccessClaims: ...


class TokenGenerator(Protocol):
    def new_secret(self) -> str: ...
    def hash(self, secret: str) -> str: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class RateLimiter(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        """Record a hit. Return the retry-after seconds when the limit is exceeded, else None."""
        ...


class LinkBuilder(Protocol):
    def link_for(self, purpose: TokenPurpose, secret: str) -> str: ...


class EmailSender(Protocol):
    async def send_link(self, to_email: str, purpose: TokenPurpose, link: str) -> bool:
        """Deliver a link. Return True only when a message was actually sent."""
        ...

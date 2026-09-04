"""Ports are typing.Protocol classes; adapters implement them; the container wires them."""

from ase.application.ports.repositories import (
    AccountRequestRepository,
    AuditLogRepository,
    PasswordTokenRepository,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.services import (
    AccessTokenIssuer,
    Clock,
    EmailSender,
    LinkBuilder,
    PasswordHasher,
    RateLimiter,
    TokenGenerator,
)

__all__ = [
    "AccessTokenIssuer",
    "AccountRequestRepository",
    "AuditLogRepository",
    "Clock",
    "EmailSender",
    "LinkBuilder",
    "PasswordHasher",
    "PasswordTokenRepository",
    "RateLimiter",
    "RefreshTokenRepository",
    "TokenGenerator",
    "UnitOfWork",
    "UserRepository",
]

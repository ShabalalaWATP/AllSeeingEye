"""Authoritative session checks, reusable by HTTP and long-lived stream consumers."""

from ase.application.dto import AccessClaims
from ase.application.ports import Clock, RefreshTokenRepository, UserRepository
from ase.domain.errors import SessionIdleExpired, Unauthenticated
from ase.domain.users import User


async def validate_current_session(
    claims: AccessClaims,
    users: UserRepository,
    refresh_tokens: RefreshTokenRepository,
    clock: Clock,
) -> User:
    """Use a fresh transaction per check, including periodic stream revalidation."""
    now = clock.now()
    user = await users.get_by_id(claims.user_id)
    if (
        claims.expires_at <= now
        or user is None
        or not user.is_active
        or user.security_version != claims.security_version
    ):
        raise Unauthenticated("The session has ended. Sign in again.")
    if not await refresh_tokens.family_is_active(
        user.id, claims.family_id, now, require_mfa=user.is_admin
    ):
        activity = await refresh_tokens.activity(user.id, claims.family_id, now)
        if activity is not None and activity.expired:
            raise SessionIdleExpired(fields={"idle_minutes": str(activity.idle_minutes)})
        raise Unauthenticated("The session has ended. Sign in again.")
    return user

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
    user = await users.get_by_id(claims.user_id)
    if (
        claims.expires_at <= clock.now()
        or user is None
        or not user.is_active
        or user.security_version != claims.security_version
    ):
        raise Unauthenticated("The session has ended. Sign in again.")
    active = await refresh_tokens.family_is_active(
        user.id, claims.family_id, clock.now(), require_mfa=user.is_admin
    )
    activity = await refresh_tokens.activity(user.id, claims.family_id, clock.now())
    # A valid database snapshot can cross either deadline while the read is
    # awaited. Check both after the final await without changing caller-owned
    # transactions or counting passive validation as activity.
    now = clock.now()
    if claims.expires_at <= now:
        raise Unauthenticated("The session has ended. Sign in again.")
    if activity is not None and activity.idle_expires_at <= now:
        raise SessionIdleExpired(fields={"idle_minutes": str(activity.idle_minutes)})
    if not active or activity is None:
        raise Unauthenticated("The session has ended. Sign in again.")
    return user

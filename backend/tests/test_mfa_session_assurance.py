"""MFA assurance belongs to the live session family and survives refresh rotation."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AuthSession, RequestContext
from ase.container import Container
from ase.domain.errors import InvalidRefreshToken, Unauthenticated
from ase.domain.users import User
from helpers import FakeClock, bearer

CONTEXT = RequestContext(ip="test", user_agent="assurance-test")


async def _start(container: Container, actor: User, *, verified: bool = False) -> AuthSession:
    """Exercise session persistence directly, independently of the login challenge UI."""
    async with container.session_factory() as session:
        repos = container.repositories(session)
        result = await container._sessions(repos).start(actor, CONTEXT, mfa_verified=verified)
        await repos.uow.commit()
        return result


async def test_existing_password_only_admin_session_cannot_access_or_refresh(
    container: Container, client: AsyncClient, admin: User
) -> None:
    old = await _start(container, admin)
    assert (await client.get("/api/me", headers=bearer(old.access.token))).status_code == 401
    assert (
        await client.get("/api/admin/users", headers=bearer(old.access.token))
    ).status_code == 401
    async with container.session_factory() as session:
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(old.refresh_secret, CONTEXT)
        token = await container.repositories(session).refresh_tokens.get_by_hash(
            container.generator.hash(old.refresh_secret)
        )
        assert token is not None and not token.mfa_verified and token.revoked_at is None


async def test_verified_admin_rotation_preserves_assurance(
    container: Container, client: AsyncClient, admin: User
) -> None:
    original = await _start(container, admin, verified=True)
    async with container.session_factory() as session:
        rotated = await container.refresh(session).execute(original.refresh_secret, CONTEXT)
    assert (await client.get("/api/me", headers=bearer(rotated.access.token))).status_code == 200
    assert (await client.get("/api/me", headers=bearer(original.access.token))).status_code == 200
    async with container.session_factory() as session:
        repo = container.repositories(session).refresh_tokens
        first = await repo.get_by_hash(container.generator.hash(original.refresh_secret))
        second = await repo.get_by_hash(container.generator.hash(rotated.refresh_secret))
        assert first is not None and second is not None
        assert first.mfa_verified and second.mfa_verified
        assert first.family_id == second.family_id and second.parent_id == first.id
        assert first.revoked_at is not None and second.revoked_at is None


async def test_non_admin_password_only_sessions_continue_to_work(
    container: Container, client: AsyncClient, user: User
) -> None:
    original = await _start(container, user)
    async with container.session_factory() as session:
        rotated = await container.refresh(session).execute(original.refresh_secret, CONTEXT)
        token = await container.repositories(session).refresh_tokens.get_by_hash(
            container.generator.hash(rotated.refresh_secret)
        )
        assert token is not None and not token.mfa_verified
    assert (await client.get("/api/me", headers=bearer(rotated.access.token))).status_code == 200


@pytest.mark.parametrize("invalidity", ["revoked", "expired", "version", "inactive"])
async def test_mfa_assurance_does_not_override_session_invalidation(
    container: Container, admin: User, clock: FakeClock, invalidity: str
) -> None:
    auth = await _start(container, admin, verified=True)
    claims = container.issuer.verify(auth.access.token)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        if invalidity == "revoked":
            await repos.refresh_tokens.revoke_family(claims.family_id, clock.now())
        elif invalidity == "expired":
            clock.advance(timedelta(days=100))
        else:
            current = await repos.users.lock_by_id(admin.id)
            assert current is not None
            if invalidity == "version":
                current.security_version += 1
            else:
                current.is_active = False
            await repos.users.save(current)
        await repos.uow.commit()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        with pytest.raises(Unauthenticated):
            await validate_current_session(claims, repos.users, repos.refresh_tokens, clock)


async def test_assurance_from_another_family_does_not_authorise_password_only_admin(
    container: Container, client: AsyncClient, admin: User
) -> None:
    old = await _start(container, admin)
    verified = await _start(container, admin, verified=True)
    assert (await client.get("/api/me", headers=bearer(verified.access.token))).status_code == 200
    assert (await client.get("/api/me", headers=bearer(old.access.token))).status_code == 401

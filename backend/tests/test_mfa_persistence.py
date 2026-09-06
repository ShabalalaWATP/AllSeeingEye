"""Challenge compare-and-swap prevents replay and lost attempt updates."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.container import Container
from ase.domain.mfa import MfaChallenge, MfaPurpose
from ase.domain.users import User
from helpers import FakeClock


async def test_challenge_round_trip_and_single_use(
    container: Container, user: User, clock: FakeClock
) -> None:
    challenge = MfaChallenge(
        token_hash="a" * 64,
        user_id=user.id,
        security_version=user.security_version,
        purpose=MfaPurpose.LOGIN,
        expires_at=clock.now() + timedelta(minutes=5),
        code_hash="synthetic-password-hash",
    )
    async with container.session_factory() as session:
        repository = SqlMfaRepository(session)
        assert await repository.get("missing") is None
        await repository.add(challenge)
        await session.commit()
    async with container.session_factory() as session:
        repository = SqlMfaRepository(session)
        stored = await repository.get(challenge.token_hash)
        assert stored == challenge
        stale = replace(stored)
        stored.attempts = 1
        assert await repository.save(stored, expected_revision=0)
        assert stored.revision == 1
        stale.attempts = 3
        assert not await repository.save(stale, expected_revision=0)
        assert (await repository.get(challenge.token_hash)) == stored
        stored.consumed_at = clock.now()
        assert await repository.save(stored, expected_revision=1)
        assert not await repository.save(stored, expected_revision=2)
        await session.commit()
    async with container.session_factory() as session:
        saved = await SqlMfaRepository(session).get(challenge.token_hash)
        assert saved and saved.consumed_at == clock.now() and saved.revision == 2


async def test_email_factor_is_scoped_and_durable(
    container: Container, user: User, admin: User
) -> None:
    async with container.session_factory() as session:
        repository = SqlMfaRepository(session)
        assert not await repository.email_enabled(user.id)
        await repository.set_email_enabled(user.id, True)
        assert await repository.email_enabled(user.id)
        assert not await repository.email_enabled(admin.id)
        await session.commit()
    async with container.session_factory() as session:
        repository = SqlMfaRepository(session)
        assert await repository.email_enabled(user.id)
        await repository.set_email_enabled(user.id, False)
        assert not await repository.email_enabled(user.id)
        await session.commit()

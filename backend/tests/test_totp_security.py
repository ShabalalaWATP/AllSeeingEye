"""Cryptographic boundary, atomic transitions and application-layer permissions."""

from dataclasses import replace
from datetime import timedelta

import pyotp
import pytest

from ase.adapters.persistence.totp import SqlTotpRepository
from ase.adapters.security.cipher import FernetCipher
from ase.adapters.security.totp import EncryptedTotpProvider
from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.errors import EncryptionUnavailable, Forbidden, InvalidRequest
from ase.domain.users import User
from helpers import ADMIN_PASSWORD, FakeClock

CONTEXT = RequestContext(ip="test", user_agent="test")


def test_provider_uses_standard_totp_and_never_exposes_secrets_in_repr(clock: FakeClock) -> None:
    provider = EncryptedTotpProvider(FernetCipher("k" * 40))
    enrolment = provider.enrol("admin@example.com")
    assert provider.available
    assert enrolment.secret not in repr(enrolment)
    totp = pyotp.parse_uri(enrolment.provisioning_uri)
    assert isinstance(totp, pyotp.TOTP)
    assert totp.secret == enrolment.secret
    assert totp.issuer == "The All Seeing Eye"
    for delta in (-30, 0, 30):
        at = clock.now() + timedelta(seconds=delta)
        assert provider.verify(enrolment.encrypted, totp.at(at), clock.now()) == totp.timecode(at)
    assert (
        provider.verify(
            enrolment.encrypted, totp.at(clock.now() - timedelta(minutes=2)), clock.now()
        )
        is None
    )
    for invalid in ("", "12345", "1234567", "\uff11\uff12\uff13\uff14\uff15\uff16", "abcdef"):
        assert provider.verify(enrolment.encrypted, invalid, clock.now()) is None


def test_missing_or_changed_encryption_key_fails_closed(clock: FakeClock) -> None:
    unavailable = EncryptedTotpProvider(FernetCipher(None))
    assert not unavailable.available
    with pytest.raises(EncryptionUnavailable):
        unavailable.enrol("admin@example.com")
    with pytest.raises(EncryptionUnavailable):
        unavailable.verify("invalid", "123456", clock.now())
    with pytest.raises(EncryptionUnavailable):
        EncryptedTotpProvider(FernetCipher("wrong" * 8)).verify("invalid", "123456", clock.now())


async def test_atomic_replay_consumption_and_stale_confirmation(
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    provider = EncryptedTotpProvider(container.cipher)
    first = provider.enrol(admin.email)
    second = provider.enrol(admin.email)
    expires = clock.now() + timedelta(minutes=10)
    async with container.session_factory() as session:
        repo = SqlTotpRepository(session)
        assert await repo.begin(admin.id, first.encrypted, expires)
        assert await repo.begin(admin.id, second.encrypted, expires)
        assert not await repo.confirm(admin.id, first.encrypted, 100, clock.now())
        assert await repo.confirm(admin.id, second.encrypted, 100, clock.now())
        assert not await repo.begin(admin.id, first.encrypted, expires)
        assert not await repo.confirm(admin.id, second.encrypted, 100, clock.now())
        assert not await repo.consume(admin.id, first.encrypted, 101)
        await session.commit()
    # Independent sessions with the same stale proof cannot both consume the step.
    async with (
        container.session_factory() as first_session,
        container.session_factory() as second_session,
    ):
        first_repo = SqlTotpRepository(first_session)
        second_repo = SqlTotpRepository(second_session)
        state = await second_repo.get(admin.id)
        assert state and state.last_step == 100
        assert await first_repo.consume(admin.id, second.encrypted, 101)
        await first_session.commit()
        assert not await second_repo.consume(admin.id, second.encrypted, 101)
        await second_session.commit()


async def test_application_permissions_and_local_recovery(
    container: Container,
    admin: User,
    user: User,
    clock: FakeClock,
) -> None:
    async with container.session_factory() as session:
        use_case = container.totp(session)
        for actor in (user, replace(admin, is_active=False)):
            with pytest.raises(Forbidden):
                await use_case.status(actor)
            with pytest.raises(Forbidden):
                await use_case.begin(actor, ADMIN_PASSWORD, CONTEXT)
            with pytest.raises(Forbidden):
                await use_case.confirm(actor, "123456", CONTEXT)
            with pytest.raises(Forbidden):
                await use_case.recover_local(actor, ADMIN_PASSWORD)
        assert await use_case.verify_login(user, None)
        with pytest.raises(InvalidRequest):
            await use_case.disable(admin, ADMIN_PASSWORD, "123456", CONTEXT)
        with pytest.raises(InvalidRequest):
            await use_case.confirm(admin, "123456", CONTEXT)
        enrolment = await use_case.begin(admin, ADMIN_PASSWORD, CONTEXT)
        await use_case.confirm(admin, pyotp.TOTP(enrolment.secret).at(clock.now()), CONTEXT)
        current_admin = await container.repositories(session).users.get_by_id(admin.id)
        assert current_admin
        admin = current_admin
        assert await use_case.status(admin) == (True, True)
        clock.advance(timedelta(minutes=1))
        with pytest.raises(InvalidRequest):
            await use_case.recover_local(admin, "wrong")
        assert await use_case.status(admin) == (True, True)
        await use_case.recover_local(admin, ADMIN_PASSWORD)
        assert await use_case.status(admin) == (False, True)
        assert await use_case.verify_login(admin, None)

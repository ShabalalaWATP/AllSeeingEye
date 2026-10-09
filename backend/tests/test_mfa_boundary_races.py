"""Challenge races cannot authorise a stale factor or an ended session."""

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from ase.application.dto import RequestContext
from ase.domain.errors import InvalidCredentials, InvalidRequest, Unauthenticated
from ase.domain.mfa import MfaMethod, MfaPurpose
from ase.domain.totp import TotpEnrolment, TotpState
from mfa_boundary_support import NOW, actor, challenge, use_case


async def test_unknown_challenge_never_locks_an_account() -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    mfa.d.repo.get.return_value = None
    with pytest.raises(InvalidCredentials):
        await mfa.d.load("unknown", MfaPurpose.LOGIN)
    mfa.d.users.lock_by_id.assert_not_awaited()


async def test_lost_challenge_update_cannot_advance_revision() -> None:
    user = actor()
    pending = challenge(user)
    mfa = use_case(user, pending)
    mfa.d.repo.save.return_value = False
    with pytest.raises(InvalidCredentials):
        await mfa.d.save(pending)
    assert pending.revision == 0
    mfa.d.uow.commit.assert_not_awaited()


@pytest.mark.parametrize("change", ["removed", "inactive", "security_version"])
async def test_ended_session_cannot_change_factors(change: str) -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    current = replace(user)
    if change == "inactive":
        current.is_active = False
    elif change == "security_version":
        current.security_version += 1
    mfa.d.users.lock_by_id.return_value = None if change == "removed" else current
    with pytest.raises(Unauthenticated):
        await mfa.d.current_actor(user)
    mfa.d.repo.save.assert_not_awaited()


@pytest.mark.parametrize("available", [False, True])
async def test_email_cannot_bypass_unavailable_or_unenrolled_factor(available: bool) -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    mfa.d.email.available = available
    with pytest.raises(InvalidCredentials if available else InvalidRequest):
        await mfa.send_email("pending", RequestContext())
    mfa.d.email.send_code.assert_not_awaited()


async def test_superseded_email_delivery_does_not_publish_old_code() -> None:
    user = actor()
    pending = challenge(user, enrol=True)
    mfa = use_case(user, pending)

    async def supersede(_email: str, _code: str) -> bool:
        mfa.d.repo.get.return_value = replace(pending, revision=pending.revision + 1)
        return True

    mfa.d.email.send_code.side_effect = supersede
    with pytest.raises(InvalidCredentials):
        await mfa.send_email("pending", RequestContext())
    assert mfa.d.repo.save.await_count == 1
    assert pending.email_sent_at is None


async def test_failed_email_delivery_erases_the_undelivered_proof() -> None:
    user = actor()
    pending = challenge(user, enrol=True)
    mfa = use_case(user, pending)
    mfa.d.email.send_code.return_value = False
    with pytest.raises(InvalidRequest, match="could not be sent"):
        await mfa.send_email("pending", RequestContext())
    assert pending.code_hash is None
    assert pending.email_sent_at is None
    assert mfa.d.repo.save.await_count == 2


@pytest.mark.parametrize("enrol,existing", [(False, False), (True, True)])
async def test_enrolment_cannot_replace_an_existing_factor(enrol: bool, existing: bool) -> None:
    user = actor()
    mfa = use_case(user, challenge(user, enrol=enrol))
    mfa.d.repo.email_enabled.return_value = existing
    with pytest.raises(InvalidCredentials):
        await mfa.enrol_app("pending", RequestContext())
    mfa.d.totp.begin.assert_not_awaited()


async def test_concurrent_enrolment_loser_cannot_save_pending_secret() -> None:
    user = actor()
    pending = challenge(user, enrol=True)
    mfa = use_case(user, pending)
    mfa.d.provider.enrol.return_value = TotpEnrolment("synthetic", "otpauth://test", "encrypted")
    mfa.d.totp.begin.return_value = False
    # Isolate the authenticator race from the emailed proof, covered separately.
    mfa.d.email.available = False
    with pytest.raises(InvalidRequest, match="enrolment changed"):
        await mfa.enrol_app("pending", RequestContext())
    assert pending.pending_encrypted is None
    mfa.d.repo.save.assert_not_awaited()


@pytest.mark.parametrize("state", ["absent", "replaced", "missing_pending"])
async def test_replaced_or_missing_enrolment_cannot_verify(state: str) -> None:
    user = actor()
    pending = challenge(user, enrol=True)
    pending.pending_encrypted = None if state == "missing_pending" else "expected"
    mfa = use_case(user, pending)
    mfa.d.totp.get.return_value = (
        None if state == "absent" else TotpState(user.id, None, "other", NOW, None)
    )
    assert not await mfa.verify_factor(pending, user, MfaMethod.AUTHENTICATOR, "123456")
    mfa.d.provider.verify.assert_not_called()
    mfa.d.totp.confirm.assert_not_awaited()


async def test_factor_removed_between_lookup_and_verification_fails_closed() -> None:
    user = actor()
    pending = challenge(user)
    mfa = use_case(user, pending)
    mfa.d.totp.get = AsyncMock(
        side_effect=[
            TotpState(user.id, "encrypted", None, None, None),
            None,
        ]
    )
    assert not await mfa.verify_factor(pending, user, MfaMethod.AUTHENTICATOR, "123456")
    mfa.d.provider.verify.assert_not_called()
    mfa.d.totp.consume.assert_not_awaited()


async def test_completed_enrolment_cannot_be_replayed_as_another_factor() -> None:
    user = actor()
    mfa = use_case(user, challenge(user, enrol=True))
    mfa.d.repo.email_enabled.return_value = True
    assert not await mfa.verify_factor(challenge(user, enrol=True), user, MfaMethod.EMAIL, "123456")

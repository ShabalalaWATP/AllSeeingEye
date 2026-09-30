"""Personal factor changes must preserve account, purpose and session boundaries."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.auth.mfa_management import MfaManagement
from ase.application.auth.recovery_codes import RecoveryCodesUseCase
from ase.application.dto import AccessClaims, RequestContext
from ase.domain.errors import Forbidden, InvalidCredentials, InvalidRequest
from ase.domain.mfa import MfaMethod, MfaPurpose
from ase.domain.totp import TotpState
from ase.domain.users import Role
from mfa_boundary_support import actor, challenge, use_case


@pytest.mark.parametrize(
    "purpose,enabled",
    [
        (MfaPurpose.EMAIL_ENROL, True),
        (MfaPurpose.EMAIL_DISABLE, False),
        (MfaPurpose.PASSWORD_CHANGE, False),
        (MfaPurpose.RECOVERY_CODES, False),
    ],
)
async def test_wrong_factor_state_cannot_start_personal_proof(purpose, enabled) -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    mfa.d.repo.email_enabled.return_value = enabled
    with pytest.raises(InvalidRequest):
        await MfaManagement(mfa).begin(user, "password", purpose, RequestContext())
    mfa.d.repo.add.assert_not_awaited()
    mfa.d.email.send_code.assert_not_awaited()


async def test_changed_delivery_request_requires_new_personal_proof() -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    mfa.send_email = AsyncMock(side_effect=InvalidCredentials)
    with pytest.raises(InvalidRequest, match="Start a new request"):
        await MfaManagement(mfa).begin(user, "password", MfaPurpose.EMAIL_ENROL, RequestContext())
    assert mfa.d.users.lock_by_id.await_count == 2
    mfa.d.repo.set_email_enabled.assert_not_awaited()


@pytest.mark.parametrize("unknown", [True, False])
async def test_personal_proof_never_consumes_another_accounts_challenge(unknown: bool) -> None:
    user = actor()
    pending = challenge(actor())
    mfa = use_case(user, pending)
    mfa.d.repo.get.return_value = None if unknown else pending
    with pytest.raises(InvalidRequest):
        await MfaManagement(mfa).consume_proof(
            user, "foreign", "123456", MfaPurpose.EMAIL_ENROL, RequestContext()
        )
    mfa.d.repo.save.assert_not_awaited()
    mfa.d.users.lock_by_id.assert_awaited_once_with(user.id)


async def test_security_version_changed_during_proof_cannot_change_factor() -> None:
    user = actor()
    pending = challenge(user)
    pending.purpose = MfaPurpose.EMAIL_ENROL
    refreshed = replace(user, security_version=1)
    refreshed_proof = replace(pending, security_version=1)
    mfa = use_case(user, pending)
    mfa.d.users.lock_by_id.side_effect = [user, refreshed]
    mfa.d.repo.get.side_effect = [pending, refreshed_proof, refreshed_proof]
    with pytest.raises(InvalidRequest):
        await MfaManagement(mfa).consume_proof(
            user, "pending", "123456", MfaPurpose.EMAIL_ENROL, RequestContext()
        )
    mfa.d.repo.save.assert_not_awaited()


async def test_administrator_cannot_remove_last_email_factor() -> None:
    user = replace(actor(), role=Role.ADMIN)
    mfa = use_case(user, challenge(user))
    mfa.d.repo.email_enabled.return_value = True
    with pytest.raises(InvalidRequest, match="at least one MFA"):
        await MfaManagement(mfa).begin(user, "password", MfaPurpose.EMAIL_DISABLE, RequestContext())
    mfa.d.repo.add.assert_not_awaited()


async def test_local_recovery_rejects_non_administrator_without_mutation() -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    with pytest.raises(Forbidden):
        await MfaManagement(mfa).recover_local(user, "password")
    mfa.d.totp.clear.assert_not_awaited()
    mfa.d.recovery.clear.assert_not_awaited()
    mfa.d.repo.set_email_enabled.assert_not_awaited()


@pytest.mark.parametrize(
    "method,enabled,methods",
    [
        (MfaMethod.AUTHENTICATOR, False, None),
        (MfaMethod.EMAIL, True, None),
        (MfaMethod.RECOVERY, False, (MfaMethod.RECOVERY,)),
    ],
)
async def test_recovery_rotation_requires_an_existing_factor_and_fresh_proof(
    method, enabled, methods
) -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    mfa.d.repo.email_enabled.return_value = enabled
    mfa.d.refresh.family_is_active.return_value = True
    mfa.d.users.get_by_id.return_value = user
    if methods is not None:
        # Defensive boundary: even a future recovery-only method list cannot bootstrap codes.
        mfa.methods = AsyncMock(return_value=methods)
    claims = AccessClaims(user.id, user.role, "jti", challenge(user).expires_at, uuid4(), 0)
    with pytest.raises(InvalidRequest):
        await RecoveryCodesUseCase(mfa).generate(
            user, claims, "password", method, "123456", None, RequestContext()
        )
    mfa.d.recovery.replace.assert_not_awaited()
    mfa.d.uow.commit.assert_not_awaited()


@pytest.mark.parametrize("proof", ["incorrect", "replayed", "removed"])
async def test_recovery_rotation_rejects_unusable_authenticator_proof(proof: str) -> None:
    user = actor()
    mfa = use_case(user, challenge(user))
    state = TotpState(user.id, "encrypted", None, None, None)
    mfa.d.totp.get.side_effect = [state, None if proof == "removed" else state]
    mfa.d.provider.verify.return_value = None if proof == "incorrect" else 42
    mfa.d.totp.consume.return_value = False
    mfa.d.refresh.family_is_active.return_value = True
    mfa.d.users.get_by_id.return_value = user
    claims = AccessClaims(user.id, user.role, "jti", challenge(user).expires_at, uuid4(), 0)
    with pytest.raises(InvalidRequest, match="incorrect or already used"):
        await RecoveryCodesUseCase(mfa).generate(
            user, claims, "password", MfaMethod.AUTHENTICATOR, "123456", None, RequestContext()
        )
    mfa.d.recovery.replace.assert_not_awaited()
    mfa.d.uow.commit.assert_not_awaited()

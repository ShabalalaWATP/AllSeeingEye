"""A per-account budget of failed second-factor proofs spans challenges, methods and clients."""

from __future__ import annotations

from datetime import timedelta

import pyotp
import pytest
from httpx import AsyncClient

from ase.application.auth.mfa_context import SECOND_FACTOR_FAILURES, SECOND_FACTOR_WINDOW_SECONDS
from ase.application.dto import AuthSession, RequestContext
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidCredentials, RateLimited
from ase.domain.mfa import MfaMethod, PendingMfa
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, FakeClock
from totp_helpers import enable_totp

CHALLENGES = 4
ATTEMPTS_PER_CHALLENGE = 5


async def _challenge(container: Container, context: RequestContext) -> str:
    async with container.session_factory() as session:
        pending = await container.login(session).execute(ADMIN_EMAIL, ADMIN_PASSWORD, context)
    assert isinstance(pending, PendingMfa)
    return pending.challenge_token


async def _verify(
    container: Container, token: str, method: MfaMethod, code: str, context: RequestContext
) -> AuthSession:
    async with container.session_factory() as session:
        return await container.mfa(session).verify(token, method, code, context)


def _wrong_code(secret: str, clock: FakeClock) -> str:
    valid = pyotp.TOTP(secret).at(clock.now())
    return "000000" if valid != "000000" else "111111"


async def _throttled_audits(container: Container) -> int:
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 200)
    return sum(
        entry.action is AuditAction.LOGIN_FAILED
        and entry.details == {"reason": "second_factor_rate_limited"}
        for entry in entries
    )


async def test_failures_across_challenges_and_clients_throttle_the_account(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock
) -> None:
    _, secret = await enable_totp(client, clock)
    # Clear the password-login and per-client second-factor windows used by enrolment.
    clock.advance(timedelta(seconds=301))
    outcomes: list[str] = []
    for index in range(CHALLENGES):
        # Every challenge comes from a different client, so only the account budget applies.
        context = RequestContext(ip=f"198.51.100.{index + 1}")
        token = await _challenge(container, context)
        for attempt in range(ATTEMPTS_PER_CHALLENGE):
            method = MfaMethod.RECOVERY if attempt % 2 else MfaMethod.AUTHENTICATOR
            code = "WRONG-RECOVERY" if method is MfaMethod.RECOVERY else _wrong_code(secret, clock)
            try:
                await _verify(container, token, method, code, context)
            except InvalidCredentials:
                outcomes.append("invalid")
            except RateLimited as exc:
                assert 0 < exc.retry_after <= SECOND_FACTOR_WINDOW_SECONDS
                outcomes.append("limited")
    total = CHALLENGES * ATTEMPTS_PER_CHALLENGE
    assert outcomes == ["invalid"] * SECOND_FACTOR_FAILURES + ["limited"] * (
        total - SECOND_FACTOR_FAILURES
    )
    assert await _throttled_audits(container) == total - SECOND_FACTOR_FAILURES

    # Even the correct code is refused while the budget is spent, without consuming it.
    context = RequestContext(ip="198.51.100.200")
    token = await _challenge(container, context)
    with pytest.raises(RateLimited):
        await _verify(
            container, token, MfaMethod.AUTHENTICATOR, pyotp.TOTP(secret).at(clock.now()), context
        )

    clock.advance(timedelta(seconds=SECOND_FACTOR_WINDOW_SECONDS + 1))
    token = await _challenge(container, context)
    session = await _verify(
        container, token, MfaMethod.AUTHENTICATOR, pyotp.TOTP(secret).at(clock.now()), context
    )
    assert session.user.email == ADMIN_EMAIL


async def test_successful_proofs_do_not_spend_the_budget(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock
) -> None:
    _, secret = await enable_totp(client, clock)
    for index in range(SECOND_FACTOR_FAILURES + 2):
        # Space sign-ins beyond the login and authenticator replay windows.
        clock.advance(timedelta(seconds=61))
        context = RequestContext(ip=f"192.0.2.{index + 1}")
        token = await _challenge(container, context)
        await _verify(
            container, token, MfaMethod.AUTHENTICATOR, pyotp.TOTP(secret).at(clock.now()), context
        )
    assert await _throttled_audits(container) == 0


async def test_http_response_is_the_existing_rate_limited_error(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock
) -> None:
    _, secret = await enable_totp(client, clock)
    clock.advance(timedelta(seconds=301))
    for index in range(SECOND_FACTOR_FAILURES // ATTEMPTS_PER_CHALLENGE):
        context = RequestContext(ip=f"198.51.100.{index + 1}")
        token = await _challenge(container, context)
        for _ in range(ATTEMPTS_PER_CHALLENGE):
            with pytest.raises(InvalidCredentials):
                await _verify(
                    container, token, MfaMethod.AUTHENTICATOR, _wrong_code(secret, clock), context
                )
    pending = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert pending.status_code == 200, pending.text
    response = await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": pending.json()["challenge_token"],
            "method": "authenticator",
            "code": pyotp.TOTP(secret).at(clock.now()),
        },
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0
    # The response carries no detail about the account or its factors.
    assert secret not in response.text

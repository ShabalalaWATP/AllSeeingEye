"""Private HTTP release rechecks after disconnect cleanup and retains no forged scope."""

from typing import Any

import pytest
from httpx import AsyncClient

from ase.api.routers import sec_filings
from ase.application.access import AccessPolicy
from ase.application.research.sec_filings import SecFilings
from ase.container import Container
from ase.domain.users import User
from helpers import CSRF_COOKIE, USER_EMAIL, USER_PASSWORD, bearer, login_token
from sec_filings_helpers import SecTransport
from test_sec_filing_api import BASE, SEARCH, selected


@pytest.mark.parametrize("operation", ["listing", "import"])
async def test_logout_during_connected_cleanup_denies_private_response(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    complete = sec_filings._complete_connected
    try:
        key = await selected(client, token) if operation == "import" else None

        async def revoke_after_cleanup(*args: Any, **kwargs: Any) -> Any:
            result = await complete(*args, **kwargs)
            assert (
                await client.post(
                    "/api/auth/logout",
                    headers={
                        "X-CSRF-Token": client.cookies[CSRF_COOKIE],
                    },
                )
            ).status_code == 204
            return result

        monkeypatch.setattr(sec_filings, "_complete_connected", revoke_after_cleanup)
        response = await client.post(
            BASE if key is None else f"{BASE}/{key}/import",
            json=SEARCH if key is None else None,
            headers=bearer(token),
        )
        assert response.status_code == 401
        assert "Synthetic Issuer" not in response.text
        assert "reported revenue" not in response.text
    finally:
        await transport.http.aclose()


@pytest.mark.parametrize("operation", ["listing", "import", "original"])
async def test_logout_during_final_access_context_precedes_last_family_check(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    try:
        key = await selected(client, token) if operation != "listing" else None
        if operation == "original":
            result = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
            assert result.status_code == 201, result.text
        method = {"listing": "release_choices", "import": "release_input", "original": "original"}[
            operation
        ]
        original = getattr(SecFilings, method)
        access_context = AccessPolicy.context
        revoked = False

        async def late_context(access: AccessPolicy, *args: Any, **kwargs: Any) -> Any:
            nonlocal revoked
            result = await access_context(access, *args, **kwargs)
            response = await client.post(
                "/api/auth/logout",
                headers={
                    "X-CSRF-Token": client.cookies[CSRF_COOKIE],
                },
            )
            assert response.status_code == 204, response.text
            revoked = True
            return result

        async def final_release(service: SecFilings, *args: Any, **kwargs: Any) -> Any:
            with monkeypatch.context() as patch:
                patch.setattr(AccessPolicy, "context", late_context)
                return await original(service, *args, **kwargs)

        monkeypatch.setattr(SecFilings, method, final_release)
        if operation == "original":
            response = await client.get(f"{BASE}/{key}/original", headers=bearer(token))
        else:
            response = await client.post(
                BASE if key is None else f"{BASE}/{key}/import",
                json=SEARCH if key is None else None,
                headers=bearer(token),
            )
        assert revoked and response.status_code == 401, response.text
        assert "Synthetic Issuer" not in response.text and "reported revenue" not in response.text
    finally:
        await transport.http.aclose()

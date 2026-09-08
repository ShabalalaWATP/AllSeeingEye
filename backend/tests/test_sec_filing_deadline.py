"""Elapsed-time deadline cancels upstream work and frees reserved private capacity."""

import asyncio

import httpx
import pytest
from httpx import AsyncClient

from ase.application.research import sec_filings
from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from sec_filings_helpers import SecTransport
from test_sec_filing_api import BASE, SEARCH, selected


@pytest.mark.parametrize("operation", ["listing", "import"])
async def test_whole_request_deadline_cancels_transport_without_retry(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    cleaned = asyncio.Event()

    async def slow(request: httpx.Request) -> None:
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    try:
        key = await selected(client, token) if operation == "import" else None
        transport.before = slow
        transport.client._last_request = 0
        monkeypatch.setattr(sec_filings, "REQUEST_SECONDS", 0.05)
        response = await client.post(
            BASE if key is None else f"{BASE}/{key}/import",
            json=SEARCH if key is None else None,
            headers=bearer(token),
        )
        assert response.status_code == 422, response.text
        assert "timed out" in response.text
        assert cleaned.is_set()
        assert len(transport.requests) == (1 if operation == "listing" else 2)
        assert not any(value.reserved for value in container.sec_selections._items.values())
    finally:
        await transport.http.aclose()

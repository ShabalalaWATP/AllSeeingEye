"""Private cache quotas, expiry, admission revocation and parser resource ceilings."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from httpx import AsyncClient

from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.research_inputs.memory import BoundedResearchInputStore
from ase.adapters.research_records.sec_document import extract
from ase.adapters.research_records.sec_selections import BoundedSecSelections
from ase.application.dto import AccessClaims
from ase.container import Container
from ase.domain.errors import NotFound, RateLimited
from ase.domain.sec_filings import SecFilingPage
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token
from research_input_helpers import actor
from sec_filings_helpers import DOCUMENT, SecTransport
from test_sec_filing_api import BASE, selected
from test_sec_filing_documents import FILING


def test_original_reservations_have_per_owner_and_global_limits_and_expire(
    clock: FakeClock,
) -> None:
    user = actor()
    claims = AccessClaims(
        user.id,
        user.role,
        "fixture",
        clock.now() + timedelta(hours=1),
        uuid4(),
        user.security_version,
    )
    store = BoundedSecSelections(clock)
    page = SecFilingPage((FILING, FILING, FILING), 0, 0, 0, None, ())
    choices = store.issue(claims, page)
    for choice in choices[:2]:
        store.reserve_original(claims, choice.selection_id)
    with pytest.raises(RateLimited):
        store.reserve_original(claims, choices[2].selection_id)
    for _ in range(6):
        foreign = replace(claims, user_id=uuid4(), family_id=uuid4())
        choice = store.issue(foreign, replace(page, items=(FILING,)))[0]
        store.reserve_original(foreign, choice.selection_id)
    foreign = replace(claims, user_id=uuid4(), family_id=uuid4())
    choice = store.issue(foreign, replace(page, items=(FILING,)))[0]
    with pytest.raises(RateLimited):
        store.reserve_original(foreign, choice.selection_id)
    with pytest.raises(NotFound):
        store.get(foreign, choices[0].selection_id)
    clock.advance(timedelta(minutes=15))
    with pytest.raises(NotFound):
        store.get(claims, choices[0].selection_id)
    assert not store._items


@pytest.mark.parametrize(
    "raw",
    [b"<div hidden>" + b"<div>" * 129, b"</x>" * 100001],
    ids=["nested-hidden", "unmatched-closers"],
)
def test_markup_limits_count_closers_and_hidden_nesting(raw: bytes, clock: FakeClock) -> None:
    with pytest.raises(ValueError, match="limit"):
        extract(raw, FILING, clock.now())


@pytest.mark.parametrize("point", ["before", "during"])
async def test_source_disabled_never_retains_filing(
    point: str,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)

    async def disable() -> None:
        async with container.session_factory() as session:
            await SqlSourceControlRepository(session).set(
                "research-sec-submissions",
                False,
                container.clock.now(),
                user.id,
            )
            await session.commit()

    async def during(request: httpx.Request) -> None:
        if str(request.url) == DOCUMENT:
            await disable()

    try:
        key = await selected(client, token)
        if point == "before":
            await disable()
        else:
            transport.before = during
        response = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
        assert response.status_code == 422, response.text
        assert "disabled" in response.text
        store = container.research_inputs
        assert isinstance(store, BoundedResearchInputStore)
        assert not store._ready and not store._reservations
        assert not any(value.reserved for value in container.sec_selections._items.values())
        assert len(transport.requests) == (1 if point == "before" else 2)
    finally:
        await transport.http.aclose()


async def test_failed_extraction_is_safe_and_retry_reuses_released_capacity(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    try:
        key = await selected(client, token)
        transport.responses[DOCUMENT] = b"<script>Private provider error detail</script>"
        response = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
        assert response.status_code == 422, response.text
        assert "Private provider" not in response.text
        transport.responses[DOCUMENT] = b"<p>Corrected public filing text.</p>"
        response = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
        assert response.status_code == 201, response.text
    finally:
        await transport.http.aclose()

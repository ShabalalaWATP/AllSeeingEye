"""Explicit authenticated lookup and final source/session checks."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from ase.application.ports.lei_candidates import LeiCandidate
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_anonymous_lookup_cannot_send_a_name(client) -> None:
    with patch("ase.adapters.research_records.gleif_candidates.GleifCandidates.search") as search:
        result = await client.post("/api/research/lei-candidates", json={"name": "Example"})
    assert result.status_code == 401
    search.assert_not_called()


@pytest.mark.usefixtures("user")
async def test_explicit_lookup_is_bounded_validated_and_not_cached(client) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    lookup = AsyncMock(
        return_value=(LeiCandidate("5493001KJTIIGC8Y1R12", "Example", "GB", "ACTIVE"),)
    )
    with patch("ase.adapters.research_records.gleif_candidates.GleifCandidates.search", lookup):
        result = await client.post(
            "/api/research/lei-candidates",
            json={"name": "Example", "country": "GB"},
            headers=bearer(token),
        )
        invalid = await client.post(
            "/api/research/lei-candidates",
            json={"name": "Example", "country": "GBR"},
            headers=bearer(token),
        )
    assert result.status_code == 200, result.text
    assert result.headers["cache-control"] == "private, no-store"
    assert result.json()["items"][0]["lei"] == "5493001KJTIIGC8Y1R12"
    assert invalid.status_code == 422
    lookup.assert_awaited_once_with("Example", "GB")


@pytest.mark.usefixtures("admin", "user")
@pytest.mark.parametrize("change", ["source_disabled", "session_revoked", "session_expired"])
async def test_pending_lookup_rechecks_source_and_original_session(
    client, container, clock, change
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    claims = container.issuer.verify(token)
    entered, release = asyncio.Event(), asyncio.Event()

    async def waiting_lookup(name, country):
        entered.set()
        await release.wait()
        return (LeiCandidate("5493001KJTIIGC8Y1R12", "Unreleased Candidate", "GB", "ACTIVE"),)

    lookup = AsyncMock(side_effect=waiting_lookup)
    with patch("ase.adapters.research_records.gleif_candidates.GleifCandidates.search", lookup):
        async with asyncio.TaskGroup() as tasks:
            pending = tasks.create_task(
                client.post(
                    "/api/research/lei-candidates",
                    json={"name": "Example", "country": "GB"},
                    headers=bearer(token),
                )
            )
            await asyncio.wait_for(entered.wait(), 3)
            try:
                if change == "source_disabled":
                    disabled = await client.patch(
                        "/api/admin/sources/research-gleif-profile/activation",
                        json={"enabled": False},
                        headers=bearer(admin_token),
                    )
                    assert disabled.status_code == 204, disabled.text
                elif change == "session_revoked":
                    async with container.session_factory() as session:
                        repos = container.repositories(session)
                        await repos.refresh_tokens.revoke_family(claims.family_id, clock.now())
                        await repos.uow.commit()
                else:
                    clock.advance(claims.expires_at - clock.now() + timedelta(seconds=1))
            finally:
                release.set()

    result = pending.result()
    assert result.status_code == (422 if change == "source_disabled" else 401), result.text
    assert "Unreleased Candidate" not in result.text
    assert "5493001KJTIIGC8Y1R12" not in result.text
    lookup.assert_awaited_once_with("Example", "GB")

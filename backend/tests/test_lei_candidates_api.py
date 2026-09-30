"""Explicit authenticated lookup and final source/session checks."""

from unittest.mock import AsyncMock, patch

import pytest

from ase.application.ports.lei_candidates import LeiCandidate
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


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

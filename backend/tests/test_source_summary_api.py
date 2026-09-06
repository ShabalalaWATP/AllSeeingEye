"""Source explanations are available to operators without exposing configuration URLs."""

from httpx import AsyncClient

from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_source_context_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/sources")
    assert response.status_code == 401


async def test_ordinary_operator_can_read_rating_basis(client: AsyncClient, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/sources", headers=bearer(token))
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    for item in items:
        assert item["rating"]["basis"]
        assert item["rating"]["scope"]
        assert item["rating"]["limitations"]
        assert "url" not in item and "error" not in item
        assert item["rating"]["policy_version"] == "ase-source-ratings-v1"

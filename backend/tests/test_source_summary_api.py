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
        assert item["kind"] in {"api", "rss", "geojson", "websocket"}
        assert isinstance(item["requires_key"], bool)
        assert item["collection_mode"] in {"scheduled", "on_demand"}
        assert item["coverage_scope"] in {"global", "regional", "unspecified"}
        assert item["coverage_note"]
        assert "credentials" not in item and "homepage" not in item


async def test_catalogue_discloses_scope_without_runtime_access_claims(
    client: AsyncClient,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/sources", headers=bearer(token))
    items = {item["id"]: item for item in response.json()["items"]}
    house = items["research-companies-house"]
    assert house["requires_key"] is True
    assert house["collection_mode"] == "on_demand"
    assert house["coverage_countries"] == ["GB"]
    assert "jurisdiction" in house["coverage_note"]
    assert items["research-openalex"]["collection_mode"] == "on_demand"
    assert items["research_import"]["coverage_scope"] == "unspecified"

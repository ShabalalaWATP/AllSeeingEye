"""The map exposes bounded, attributed public snapshots only after authentication."""

from httpx import AsyncClient

from ase.adapters.geo.infrastructure import public_infrastructure
from ase.api.schemas_infrastructure import InfrastructureOut
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


def test_snapshot_geometry_and_provenance() -> None:
    data = InfrastructureOut.model_validate(public_infrastructure())
    assert 1000 < len(data.cables) <= 3000
    assert len(data.ground_stations) >= 25
    assert len({c.id for c in data.cables}) == len(data.cables)
    assert len({s.id for s in data.ground_stations}) == len(data.ground_stations)
    for cable in data.cables:
        assert 2 <= len(cable.path) <= 512
        assert cable.source_url.startswith("https://www.openstreetmap.org/way/")
        assert "approximate" in cable.note
        assert all(-180 <= lon <= 180 and -90 <= lat <= 90 for lon, lat in cable.path)
    for station in data.ground_stations:
        assert station.source_url.startswith("https://")
        assert len(station.country) == 2
        assert station.note
    assert "OpenStreetMap" in data.cable_attribution
    assert data.cable_licence_url == "https://www.openstreetmap.org/copyright"


async def test_snapshot_requires_login(client: AsyncClient, user: User) -> None:
    assert (await client.get("/api/map-infrastructure")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/map-infrastructure", headers=bearer(token))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()
    assert len(payload["cables"]) >= 1000
    assert payload["ground_stations"]
    assert "api_key" not in response.text

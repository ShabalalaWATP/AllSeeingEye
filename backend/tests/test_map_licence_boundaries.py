"""Commercial asset policy rejects work before contacting providers or releasing caches."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from ase.application.cameras import CameraCatalogueService
from ase.application.dto import RequestContext
from ase.application.footprints import FootprintSearchUseCase
from ase.application.navigation import RoutePlanner
from ase.application.place_search import PlaceSearch
from ase.application.terrain import TerrainSampler
from ase.domain.errors import Forbidden
from ase.domain.events import Point
from ase.domain.source_licences import LICENCE_UNAVAILABLE, SourceLicencePolicy
from test_camera_catalogue_states import source
from test_copernicus_footprints import QUERY


async def test_blocked_camera_preserves_status_without_fetching_or_releasing_cache(user, clock):
    provider = source()
    policy = SourceLicencePolicy((), commercial_use=True)
    service = CameraCatalogueService((provider,), clock, licences=policy)
    cached = service._sources[0]
    cached.cameras = provider.fetch.return_value
    cached.fetched_at = clock.now()

    result = await service.catalogue(user, "tfl")

    provider.fetch.assert_not_awaited()
    assert result.cameras == service.snapshot(user).cameras == ()
    assert result.providers[0].status == "licence_blocked"
    assert result.providers[0].count == 0
    assert "licence terms" in result.providers[0].message
    with pytest.raises(Forbidden, match="licence terms"):
        await service.frame(user, "tfl", "1")
    provider.frame.assert_not_awaited()


@pytest.mark.parametrize("operation", ["terrain", "places", "route"])
async def test_blocked_map_service_never_calls_gateway(user, operation):
    gateway, limiter = AsyncMock(), Mock()
    licences = SourceLicencePolicy((), commercial_use=True)
    with pytest.raises(Forbidden, match="licence terms"):
        if operation == "terrain":
            await TerrainSampler(gateway, limiter, licences=licences).sample(
                user.id, (Point(0, 51),)
            )
        elif operation == "places":
            await PlaceSearch(gateway, limiter, licences=licences).search(user.id, "London")
        else:
            await RoutePlanner(gateway, limiter, licences=licences).calculate(
                user.id, "walking", (Point(0, 51), Point(0.01, 51))
            )
    assert gateway.mock_calls == []
    assert limiter.mock_calls == []


async def test_blocked_footprints_explain_licence_veto_before_query(user, clock):
    provider, limiter = Mock(), Mock()
    admission = SimpleNamespace(
        enabled=AsyncMock(return_value=False),
        licence_denial=Mock(return_value=LICENCE_UNAVAILABLE),
    )
    result = await FootprintSearchUseCase(provider, limiter, clock, admission).execute(
        user, QUERY, RequestContext("local", "test"), AsyncMock()
    )
    assert result.status == "unavailable"
    assert result.limitations == LICENCE_UNAVAILABLE
    assert not provider.mock_calls and not limiter.mock_calls

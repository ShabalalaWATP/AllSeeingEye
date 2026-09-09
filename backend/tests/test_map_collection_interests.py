"""Collection interests are bounded hints, never a requirement to read the cache."""

from unittest.mock import Mock
from uuid import uuid4

from pydantic import SecretStr

from ase.adapters.feeds.firms_runtime import ManagedFirmsConnector
from ase.application.feeds.map_interests import MapCollectionInterests
from ase.application.ports.feeds import EventQuery
from ase.container import Container
from ase.domain.events import BoundingBox, Category


def test_admits_dateline_centre_only_for_geographic_aircraft_queries():
    queue, limiter = Mock(), Mock()
    limiter.hit.return_value = None
    service = MapCollectionInterests(queue, limiter)
    user = uuid4()
    bbox = BoundingBox(170, -20, -170, 10)
    service.request(user, EventQuery(bbox=bbox, sampling="geographic"))
    queue.request.assert_called_once_with(-5, -180)
    limiter.hit.assert_called_once_with(f"map-aircraft:{user}", 60, 60)
    queue.reset_mock()
    for query in (
        EventQuery(bbox=bbox),
        EventQuery(sampling="geographic"),
        EventQuery(bbox=BoundingBox(-180, -90, 180, 90), sampling="geographic"),
        EventQuery(bbox=bbox, sampling="geographic", categories=frozenset({Category.SPACE})),
    ):
        service.request(user, query)
    queue.request.assert_not_called()


def test_excess_interests_are_ignored_without_breaking_reads():
    queue, limiter = Mock(), Mock()
    limiter.hit.return_value = 20
    MapCollectionInterests(queue, limiter).request(
        uuid4(), EventQuery(bbox=BoundingBox(-5, 50, 5, 60), sampling="geographic")
    )
    queue.request.assert_not_called()


async def test_worldwide_runtime_wires_interests_and_both_managed_sensors(settings, clock):

    runtime = Container(
        settings.model_copy(update={"firms_map_key": SecretStr("mock-test-only-key")}), clock=clock
    )
    try:
        ids = {source.spec.id for source in runtime.connectors}
        assert {"adsb_global", "adsb_viewport", "firms_viirs_noaa20", "firms_viirs_noaa21"} <= ids
        assert not {"firms_public_noaa20", "firms_public_noaa21"} & ids
        sensors = [
            source for source in runtime.connectors if isinstance(source, ManagedFirmsConnector)
        ]
        assert len(sensors) == 2
        assert all(source.http is runtime.public_firms_http for source in sensors)
        runtime.map_interests.request(
            uuid4(), EventQuery(bbox=BoundingBox(140, -40, 150, -30), sampling="geographic")
        )
        area = runtime.aircraft_interests.take()[0]
        assert (area.lat, area.lon) == (-35, 145)
    finally:
        await runtime.dispose()

"""Composition of map catalogues, routing, imagery and terrain services."""

from typing import TYPE_CHECKING

from ase.adapters.feeds.adsb_viewport import AircraftInterestQueue
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_registry import build_sources as build_camera_sources
from ase.adapters.research_records.copernicus import CopernicusFootprintProvider
from ase.adapters.routing.groundwave import NtiaGroundwaveSolver
from ase.adapters.routing.photon import PhotonPlaceSearchGateway
from ase.adapters.routing.terrarium import TERRAIN_TILE_BYTES, TerrariumGateway
from ase.adapters.routing.valhalla import ValhallaRoutingGateway
from ase.application.cameras import CameraCatalogueService
from ase.application.feeds.map_interests import MapCollectionInterests
from ase.application.footprints import FootprintSearchUseCase
from ase.application.groundwave import GroundwaveStudy
from ase.application.navigation import RoutePlanner
from ase.application.place_search import PlaceSearch
from ase.application.terrain import TerrainSampler

if TYPE_CHECKING:
    from ase.adapters.feeds.digitraffic_http import DigitrafficHttpClient
    from ase.application.ports import Clock, RateLimiter
    from ase.application.ports.source_controls import SourceAdmission
    from ase.infrastructure.settings import Settings


class MapWiring:
    if TYPE_CHECKING:
        settings: Settings
        http: FeedHttpClient
        marine_http: DigitrafficHttpClient
        clock: Clock
        limiter: RateLimiter
        source_admission: SourceAdmission

    def _initialise_map_catalogues(self) -> None:
        self.groundwave_study = GroundwaveStudy(NtiaGroundwaveSolver(), self.limiter)
        self.aircraft_interests = AircraftInterestQueue(self.clock)
        self.map_interests = MapCollectionInterests(self.aircraft_interests, self.limiter)
        self.routing_http = FeedHttpClient(self.http.user_agent, max_bytes=2 * 1024 * 1024)
        self.route_planner = RoutePlanner(ValhallaRoutingGateway(self.routing_http), self.limiter)
        self.place_search = PlaceSearch(PhotonPlaceSearchGateway(self.routing_http), self.limiter)
        self.terrain_http = FeedHttpClient(
            self.http.user_agent, max_bytes=TERRAIN_TILE_BYTES, timeout_seconds=10
        )
        self.terrain_gateway = TerrariumGateway(self.terrain_http)
        self.terrain_sampler = TerrainSampler(self.terrain_gateway, self.limiter)
        self.public_firms_http = FeedHttpClient(self.http.user_agent, max_bytes=16 * 1024 * 1024)
        self.camera_http = CameraHttpClient(self.http.user_agent, max_bytes=10 * 1024 * 1024)
        self.cameras = CameraCatalogueService(
            build_camera_sources(
                self.camera_http,
                self.marine_http,
                wsdot_access_code=(
                    self.settings.wsdot_access_code.get_secret_value()
                    if self.settings.wsdot_access_code
                    else None
                ),
            ),
            self.clock,
        )
        self.footprints = FootprintSearchUseCase(
            CopernicusFootprintProvider(self.http, self.clock),
            self.limiter,
            self.clock,
            admission=self.source_admission,
        )

"""Enumerate supported source identities without a database, credentials or provider requests."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

from ase.adapters.cyber_reference import MITRE_ATTACK_SPEC
from ase.adapters.feeds.adsb_viewport import AircraftInterestQueue
from ase.adapters.feeds.firms import sensor_spec
from ase.adapters.feeds.firms_sensors import FIRMS_SENSORS
from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS_SPEC
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.radar_attack_trends import SPEC as RADAR_ATTACK_SPEC
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.youtube import spec_for
from ase.adapters.feeds.youtube_channel_seeds import load_channels
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_registry import build_sources
from ase.adapters.geo.public_figures import load_public_figures
from ase.adapters.reference import load_reference
from ase.application.cameras import CameraCatalogueService
from ase.application.source_assets import SourceAsset
from ase.container import Container
from ase.container.economy import ECB_SPEC
from ase.container.research_sources import research_source_specs
from ase.container.source_assets import build_source_assets
from ase.container.source_requirements import OPTIONAL_CONNECTOR_SPECS
from ase.domain.sources import SourceSpec
from ase.domain.users import Role, User
from ase.infrastructure.settings import Settings

NOW = datetime(2026, 10, 9, tzinfo=UTC)


class CatalogueClock:
    def now(self) -> datetime:
        return NOW


def catalogue_specs() -> list[SourceSpec]:
    # Constructor dependencies are deliberately unusable for HTTP requests.
    http = cast(FeedHttpClient, object())
    clock = CatalogueClock()
    public = build_connectors(
        http,
        clock,
        digitraffic_http=http,
        aircraft_interests=AircraftInterestQueue(clock),
        satellite_cache_dir=None,
    )
    # Union both supported routes: configuring ReliefWeb/FIRMS would replace their
    # public alternatives, and unconfigured YouTube does not join the scheduler.
    return [
        *(connector.spec for connector in public),
        GOOGLE_NEWS_SPEC,
        *(sensor_spec(sensor) for sensor in FIRMS_SENSORS),
        *OPTIONAL_CONNECTOR_SPECS,
        *(spec_for(channel) for channel in load_channels()),
        *research_source_specs(),
        MITRE_ATTACK_SPEC,
        RADAR_ATTACK_SPEC,
        ECB_SPEC,
    ]


def catalogue_assets() -> list[SourceAsset]:
    # model_construct supplies declared defaults without .env/environment loading.
    settings = Settings.model_construct()
    sources = build_sources(cast(CameraHttpClient, object()), cast(FeedHttpClient, object()))
    context = SimpleNamespace(
        settings=settings,
        cameras=CameraCatalogueService(sources, CatalogueClock()),
        ukraine_control=None,
        ukraine_outlines=(),
        ukraine_confirmed=None,
        ukraine_civilian_harm=None,
        ukraine_reference=None,
        figure_catalogue=load_public_figures(),
        reference_catalogue=load_reference(),
        conflicts=SimpleNamespace(all=lambda: ()),
    )
    actor = User(
        UUID(int=1),
        "catalogue@example.invalid",
        "Catalogue",
        Role.USER,
        True,
        None,
        0,
        None,
        None,
        NOW,
        None,
    )
    return build_source_assets(cast(Container, context), actor)

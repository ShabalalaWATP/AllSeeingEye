"""Research and feed factories using the installation's already initialised services."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ase.adapters.feeds.firms_runtime import ManagedFirmsConnector
from ase.adapters.feeds.firms_sensors import FIRMS_SENSORS
from ase.adapters.feeds.google_news import GoogleNewsWatchlistConnector
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.persistence.watchlists import SqlWatchlistPlanStore
from ase.application.ports.feeds import FeedConnector
from ase.application.research.service import ResearchCollectionService
from ase.container.research import research_service
from ase.container.source_requirements import source_requirements
from ase.infrastructure.settings import Environment

if TYPE_CHECKING:
    from ase.container import Container


def build_research_service(container: Container) -> ResearchCollectionService:
    settings = container.settings
    return research_service(
        container.http,
        container.clock,
        tuple(settings.disabled_feed_ids),
        admission=container.source_admission,
        requirements=source_requirements(settings),
        retained_store=container.store,
        sec_client=container.sec_client,
        ooni_noncommercial_use_acknowledged=settings.ooni_noncommercial_use_acknowledged,
        ioda_public_data_use_acknowledged=settings.ioda_public_data_use_acknowledged,
        radar_reader=container.radar_attack_trends,
        radar_noncommercial_use_acknowledged=(
            settings.cloudflare_radar_noncommercial_use_acknowledged
        ),
        uksl_snapshot_path=settings.uksl_snapshot_path,
        ofac_sdn_snapshot_path=settings.ofac_sdn_snapshot_path,
        aiddata_catalogue_path=settings.aiddata_catalogue_path,
        countries=container.countries,
        companies_house_key=(
            settings.companies_house_key.get_secret_value()
            if settings.companies_house_key
            else None
        ),
        certificate_transparency_key=(
            settings.certificate_transparency_key.get_secret_value()
            if settings.certificate_transparency_key
            else None
        ),
        openalex_api_key=(
            settings.openalex_api_key.get_secret_value() if settings.openalex_api_key else None
        ),
        openaq_api_key=(
            settings.openaq_api_key.get_secret_value() if settings.openaq_api_key else None
        ),
        youtube_api_key=(
            settings.youtube_api_key.get_secret_value() if settings.youtube_api_key else None
        ),
    )


def build_feed_connectors(
    container: Container, connectors: Sequence[FeedConnector] | None
) -> list[FeedConnector]:
    settings = container.settings
    result: list[FeedConnector] = (
        list(connectors)
        if connectors is not None
        else [
            *build_connectors(
                container.http,
                container.clock,
                settings.disabled_feed_ids,
                digitraffic_http=container.marine_http,
                barentswatch_http=container.barentswatch_http,
                barentswatch_client_id=settings.barentswatch_client_id,
                barentswatch_client_secret=settings.barentswatch_client_secret,
                aircraft_interests=container.aircraft_interests,
                public_firms_http=container.public_firms_http,
                satellite_http=container.satellite_http,
                satellite_cache_dir=(
                    settings.satellite_cache_dir if settings.env is not Environment.TEST else None
                ),
                include_public_firms=not bool(settings.firms_map_key),
                ucdp_candidate_version=settings.ucdp_candidate_version,
                ucdp_access_token=(
                    settings.ucdp_access_token.get_secret_value()
                    if settings.ucdp_access_token
                    else None
                ),
                acled_access_token=(
                    settings.acled_access_token.get_secret_value()
                    if settings.acled_access_token
                    else None
                ),
                acled_tokens=container.acled_tokens,
                reliefweb_appname=settings.reliefweb_appname,
                cloudflare_radar_token=(
                    settings.cloudflare_radar_token.get_secret_value()
                    if settings.cloudflare_radar_token
                    else None
                ),
                iso3_to_iso2={
                    country.iso3: country.iso2 for country in container.countries.countries()
                },
                aisstream_key=settings.aisstream_api_key.get_secret_value()
                if settings.aisstream_api_key
                else None,
                youtube_api_key=settings.youtube_api_key.get_secret_value()
                if settings.youtube_api_key
                else None,
            ),
            *[
                ManagedFirmsConnector(
                    container.session_factory,
                    container.public_firms_http,
                    container.clock,
                    container.cipher,
                    environment_key=settings.firms_map_key.get_secret_value()
                    if settings.firms_map_key
                    else None,
                    area=settings.firms_area,
                    disabled="firms_viirs_noaa20" in settings.disabled_feed_ids
                    or f"firms_viirs_{sensor.suffix}" in settings.disabled_feed_ids,
                    sensor=sensor,
                )
                for sensor in FIRMS_SENSORS
            ],
        ]
    )
    watchlists = GoogleNewsWatchlistConnector(
        container.http, container.clock, SqlWatchlistPlanStore(container.session_factory)
    )
    if connectors is None and watchlists.spec.id not in settings.disabled_feed_ids:
        result.append(watchlists)
    return result

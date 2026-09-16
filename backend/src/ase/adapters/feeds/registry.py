"""Builds the connector set for this deployment. Keyed sources join only when their key exists."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from pydantic import SecretStr

from ase.adapters.feeds.acled_tokens import AcledTokens
from ase.adapters.feeds.adsb import LADD, PIA, AdsbListConnector, AdsbMilitaryConnector
from ase.adapters.feeds.adsb_classification import AircraftClassificationCache
from ase.adapters.feeds.adsb_global import AdsbGlobalConnector
from ase.adapters.feeds.adsb_viewport import AdsbViewportConnector, AircraftInterestQueue
from ase.adapters.feeds.adsb_watch import AdsbAreaConnector, AdsbSquawkConnector
from ase.adapters.feeds.aisstream import AisStreamConnector
from ase.adapters.feeds.barentswatch import BarentsWatchConnector
from ase.adapters.feeds.barentswatch_http import BarentsWatchHttpClient
from ase.adapters.feeds.cisa_kev import CisaKevConnector
from ase.adapters.feeds.conflict_acled import AcledConnector
from ase.adapters.feeds.conflict_reliefweb import ReliefWebReportsConnector
from ase.adapters.feeds.conflict_ucdp import UcdpCandidateConnector
from ase.adapters.feeds.conflict_ucdp_public import UcdpPublicCandidateConnector
from ase.adapters.feeds.cyber import IodaConnector, RansomwareConnector
from ase.adapters.feeds.cyclones import (
    NHC_ATLANTIC,
    NHC_EAST_PACIFIC,
    JtwcConnector,
    NhcConnector,
)
from ase.adapters.feeds.digitraffic import DigitrafficConnector
from ase.adapters.feeds.emsc import EmscConnector
from ase.adapters.feeds.eonet import EonetConnector
from ase.adapters.feeds.firms import FirmsConnector
from ase.adapters.feeds.firms_public import FirmsPublicConnector
from ase.adapters.feeds.firms_sensors import FIRMS_SENSORS
from ase.adapters.feeds.gdacs import GdacsConnector
from ase.adapters.feeds.gdelt_events import GdeltEventsConnector
from ase.adapters.feeds.gdelt_news import GdeltNewsConnector
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.humanitarian import IfrcGoConnector, WhoOutbreakConnector
from ase.adapters.feeds.isw_assessments import IswAssessmentsConnector
from ase.adapters.feeds.mastodon import MastodonConnector
from ase.adapters.feeds.mastodon_watch import load_watch
from ase.adapters.feeds.navarea import NavareaConnector
from ase.adapters.feeds.network_outages import CloudflareRadarConnector, IodaEventsConnector
from ase.adapters.feeds.nws import NwsAlertsConnector
from ase.adapters.feeds.rss_sources import build_rss_connectors
from ase.adapters.feeds.satellites import SATELLITE_SPECS, SatelliteConnector
from ase.adapters.feeds.space import KpConnector, LaunchConnector
from ase.adapters.feeds.swpc import SwpcAlertsConnector, SwpcScalesConnector
from ase.adapters.feeds.telegram import TelegramChannelConnector
from ase.adapters.feeds.telegram_channels import TELEGRAM_CHANNELS
from ase.adapters.feeds.tsunami import NTWC, PTWC, TsunamiConnector
from ase.adapters.feeds.ukraine_general_staff import GeneralStaffLossesConnector
from ase.adapters.feeds.usgs import UsgsConnector
from ase.adapters.feeds.volcanoes import VolcanoReportConnector
from ase.application.ports import Clock
from ase.application.ports.feeds import FeedConnector


def build_connectors(
    http: FeedHttpClient,
    clock: Clock,
    disabled: Iterable[str] = (),
    *,
    firms_key: str | None = None,
    aisstream_key: str | None = None,
    barentswatch_http: BarentsWatchHttpClient | None = None,
    barentswatch_client_id: SecretStr | None = None,
    barentswatch_client_secret: SecretStr | None = None,
    aircraft_interests: AircraftInterestQueue | None = None,
    firms_area: str = "world",
    digitraffic_http: FeedHttpClient | None = None,
    public_firms_http: FeedHttpClient | None = None,
    firms_http: FeedHttpClient | None = None,
    include_public_firms: bool = True,
    satellite_cache_dir: Path | None = None,
    satellite_http: FeedHttpClient | None = None,
    ucdp_candidate_version: str = "26.0.7",
    ucdp_access_token: str | None = None,
    acled_access_token: str | None = None,
    acled_tokens: AcledTokens | None = None,
    reliefweb_appname: str | None = None,
    cloudflare_radar_token: str | None = None,
    iso3_to_iso2: Mapping[str, str] | None = None,
) -> list[FeedConnector]:
    excluded = {item.strip() for item in disabled if item.strip()}
    classifications = AircraftClassificationCache()
    connectors: list[FeedConnector] = [
        UsgsConnector(http, clock),
        GdacsConnector(http, clock),
        EonetConnector(http, clock),
        SwpcAlertsConnector(http, clock),
        SwpcScalesConnector(http, clock),
        CisaKevConnector(http, clock),
        GdeltEventsConnector(http, clock),
        GdeltNewsConnector(http, clock),
        AdsbMilitaryConnector(http, clock, classifications=classifications),
        AdsbListConnector(
            http,
            clock,
            LADD,
            subtype="ladd_aircraft",
            tags=frozenset({"ladd"}),
            classifications=classifications,
        ),
        AdsbListConnector(
            http,
            clock,
            PIA,
            subtype="pia_aircraft",
            tags=frozenset({"pia"}),
            classifications=classifications,
        ),
        AdsbSquawkConnector(http, clock, classifications=classifications),
        AdsbAreaConnector(http, clock, classifications=classifications),
        AdsbGlobalConnector(http, clock, classifications=classifications),
        EmscConnector(http, clock),
        NhcConnector(http, clock, NHC_ATLANTIC),
        NhcConnector(http, clock, NHC_EAST_PACIFIC),
        JtwcConnector(http, clock),
        VolcanoReportConnector(http, clock),
        TsunamiConnector(http, clock, NTWC),
        TsunamiConnector(http, clock, PTWC),
        NwsAlertsConnector(http, clock),
        WhoOutbreakConnector(http, clock),
        IfrcGoConnector(http, clock),
        NavareaConnector(http, clock),
        *[
            SatelliteConnector(satellite_http or http, clock, spec, cache_dir=satellite_cache_dir)
            for spec in SATELLITE_SPECS
        ],
        LaunchConnector(http, clock),
        KpConnector(http, clock),
        RansomwareConnector(http, clock),
        IodaConnector(http, clock),
        IswAssessmentsConnector(http, clock),
        GeneralStaffLossesConnector(http, clock),
        IodaEventsConnector(http, clock),
        *[
            connector
            for connector in build_rss_connectors(http, clock)
            if not reliefweb_appname or connector.spec.id != "reliefweb_updates"
        ],
        *[
            MastodonConnector(http, clock, watch.instance, watch.tags, watch.minutes)
            for watch in load_watch()
        ],
        *[TelegramChannelConnector(http, clock, entry) for entry in TELEGRAM_CHANNELS],
    ]
    if aircraft_interests is not None and "adsb_viewport" not in excluded:
        connectors.append(
            AdsbViewportConnector(http, clock, aircraft_interests, classifications=classifications)
        )
    if "ucdp_candidate" not in excluded:
        connectors.append(
            UcdpCandidateConnector(http, clock, ucdp_access_token, ucdp_candidate_version)
            if ucdp_access_token
            else UcdpPublicCandidateConnector(http, clock, ucdp_candidate_version)
        )
    if (acled_tokens or acled_access_token) and AcledConnector.spec.id not in excluded:
        # A refresh token renews itself; a manual access token expires within a day.
        connectors.append(AcledConnector(http, clock, acled_access_token, tokens=acled_tokens))
    if cloudflare_radar_token and CloudflareRadarConnector.spec.id not in excluded:
        connectors.append(CloudflareRadarConnector(http, clock, cloudflare_radar_token))
    if reliefweb_appname and ReliefWebReportsConnector.spec.id not in excluded:
        connectors.append(ReliefWebReportsConnector(http, clock, reliefweb_appname, iso3_to_iso2))
    if aisstream_key and AisStreamConnector.spec.id not in excluded:
        connectors.append(AisStreamConnector(aisstream_key, clock))
    if (
        barentswatch_http is not None
        and barentswatch_client_id is not None
        and barentswatch_client_id.get_secret_value().strip()
        and barentswatch_client_secret is not None
        and barentswatch_client_secret.get_secret_value().strip()
        and BarentsWatchConnector.spec.id not in excluded
    ):
        connectors.append(
            BarentsWatchConnector(
                barentswatch_http, clock, barentswatch_client_id, barentswatch_client_secret
            )
        )
    if firms_key and FirmsConnector.spec.id not in excluded:
        for sensor in FIRMS_SENSORS:
            connectors.append(
                FirmsConnector(
                    firms_http or public_firms_http or http,
                    clock,
                    firms_key,
                    firms_area,
                    sensor=sensor,
                )
            )
    elif not firms_key and include_public_firms and FirmsPublicConnector.spec.id not in excluded:
        for sensor in FIRMS_SENSORS:
            connectors.append(
                FirmsPublicConnector(public_firms_http or firms_http or http, clock, sensor=sensor)
            )
    if digitraffic_http is not None and DigitrafficConnector.spec.id not in excluded:
        connectors.append(DigitrafficConnector(digitraffic_http, clock))
    return [connector for connector in connectors if connector.spec.id not in excluded]

"""Builds the connector set for this deployment. Keyed sources join only when their key exists."""

from __future__ import annotations

from collections.abc import Iterable

from ase.adapters.feeds.adsb import LADD, PIA, AdsbListConnector, AdsbMilitaryConnector
from ase.adapters.feeds.adsb_watch import AdsbAreaConnector, AdsbSquawkConnector
from ase.adapters.feeds.cisa_kev import CisaKevConnector
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
from ase.adapters.feeds.gdacs import GdacsConnector
from ase.adapters.feeds.gdelt_events import GdeltEventsConnector
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.humanitarian import IfrcGoConnector, WhoOutbreakConnector
from ase.adapters.feeds.mastodon import MastodonConnector, load_watch
from ase.adapters.feeds.navarea import NavareaConnector
from ase.adapters.feeds.nws import NwsAlertsConnector
from ase.adapters.feeds.rss_sources import build_rss_connectors
from ase.adapters.feeds.space import KpConnector, LaunchConnector, SatelliteConnector
from ase.adapters.feeds.swpc import SwpcAlertsConnector, SwpcScalesConnector
from ase.adapters.feeds.tsunami import NTWC, PTWC, TsunamiConnector
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
    firms_area: str = "world",
    digitraffic_http: FeedHttpClient | None = None,
) -> list[FeedConnector]:
    excluded = {item.strip() for item in disabled if item.strip()}
    connectors: list[FeedConnector] = [
        UsgsConnector(http, clock),
        GdacsConnector(http, clock),
        EonetConnector(http, clock),
        SwpcAlertsConnector(http, clock),
        SwpcScalesConnector(http, clock),
        CisaKevConnector(http, clock),
        GdeltEventsConnector(http, clock),
        AdsbMilitaryConnector(http, clock),
        AdsbListConnector(http, clock, LADD, subtype="ladd_aircraft", tags=frozenset({"ladd"})),
        AdsbListConnector(http, clock, PIA, subtype="pia_aircraft", tags=frozenset({"pia"})),
        AdsbSquawkConnector(http, clock),
        AdsbAreaConnector(http, clock),
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
        SatelliteConnector(http, clock),
        LaunchConnector(http, clock),
        KpConnector(http, clock),
        RansomwareConnector(http, clock),
        IodaConnector(http, clock),
        *build_rss_connectors(http, clock),
        *[MastodonConnector(http, clock, instance, tags) for instance, tags in load_watch()],
    ]
    if firms_key and FirmsConnector.spec.id not in excluded:
        connectors.append(FirmsConnector(http, clock, firms_key, firms_area))
    if digitraffic_http is not None and DigitrafficConnector.spec.id not in excluded:
        connectors.append(DigitrafficConnector(digitraffic_http, clock))
    return [connector for connector in connectors if connector.spec.id not in excluded]

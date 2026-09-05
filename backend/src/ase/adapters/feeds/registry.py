"""Builds the connector set for this deployment. Keyed sources join only when their key exists."""

from __future__ import annotations

from collections.abc import Iterable

from ase.adapters.feeds.cisa_kev import CisaKevConnector
from ase.adapters.feeds.eonet import EonetConnector
from ase.adapters.feeds.gdacs import GdacsConnector
from ase.adapters.feeds.gdelt_events import GdeltEventsConnector
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_sources import build_rss_connectors
from ase.adapters.feeds.swpc import SwpcAlertsConnector, SwpcScalesConnector
from ase.adapters.feeds.usgs import UsgsConnector
from ase.application.ports import Clock
from ase.application.ports.feeds import FeedConnector


def build_connectors(
    http: FeedHttpClient, clock: Clock, disabled: Iterable[str] = ()
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
        *build_rss_connectors(http, clock),
    ]
    return [connector for connector in connectors if connector.spec.id not in excluded]

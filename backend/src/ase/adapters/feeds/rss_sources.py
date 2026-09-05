"""The seeded RSS and Atom sources: official feeds first, then outlets.

Rows, not code: each seed is a SourceSpec plus the options that turn its items into
events. Feeds that answered 404 or 403 to a polite fetch (Kyiv Independent, Focus Taiwan,
NHK World, ISW, Kyodo) are left out until their URLs are confirmed.
"""

from __future__ import annotations

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.rss_seeds import US_ADVISORY, RssSeed
from ase.adapters.feeds.rss_seeds_official import OFFICIAL_SEEDS
from ase.adapters.feeds.rss_seeds_outlets import OUTLET_SEEDS
from ase.application.ports import Clock

__all__ = ["RSS_SEEDS", "US_ADVISORY", "RssSeed", "build_rss_connectors"]

RSS_SEEDS: tuple[RssSeed, ...] = (*OFFICIAL_SEEDS, *OUTLET_SEEDS)


def build_rss_connectors(http: FeedHttpClient, clock: Clock) -> list[RssConnector]:
    return [RssConnector(http, clock, seed.spec, seed.options) for seed in RSS_SEEDS]

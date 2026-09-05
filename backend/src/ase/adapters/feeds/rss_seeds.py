"""Shared pieces for the seeded RSS and Atom sources: options, the seed row and its builder.

Rows, not code: each seed is a SourceSpec plus the options that turn its items into
events. Grades follow docs/02_DATA_SOURCES.md (B for wires and public broadcasters, C
for national press, C with `state_controlled` for state media). Feeds that answered
404 or 403 to a polite fetch (Kyiv Independent, Focus Taiwan, NHK World, ISW, Kyodo)
are left out until their URLs are confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from ase.adapters.feeds.rss import RssOptions
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.sources import SourceKind, SourceSpec

OGL = "Open Government Licence v3"
OUTLET_NOTE = "Outlet terms; headlines and links only, no full text stored"
OFFICIAL = RssOptions(
    subtype="statement",
    tags=frozenset({"official"}),
    credibility=Credibility.PROBABLY_TRUE,
    rationale="Official publication by the issuing body",
)
ADVISORY = RssOptions(
    subtype="travel_advice",
    tags=frozenset({"official", "travel"}),
    credibility=Credibility.PROBABLY_TRUE,
    rationale="Official travel advice from the issuing government",
)
US_ADVISORY = RssOptions(
    subtype="travel_advisory",
    tags=frozenset({"official", "travel"}),
    credibility=Credibility.PROBABLY_TRUE,
    rationale="Official travel advisory from the issuing government",
    country_category_domain="Country-Tag",
)
WIRE = RssOptions(rationale="Established outlet report, not yet corroborated")
PRESS = RssOptions(rationale="National press report, not yet corroborated")
STATE_MEDIA = RssOptions(
    tags=frozenset({"state_controlled"}),
    credibility=Credibility.DOUBTFUL,
    rationale="State-controlled outlet; treat as the government's position",
)


@dataclass(frozen=True, slots=True)
class RssSeed:
    spec: SourceSpec
    options: RssOptions = field(default_factory=RssOptions)


def seed(
    source_id: str,
    name: str,
    organisation: str,
    category: Category,
    url: str,
    reliability: Reliability,
    minutes: int,
    options: RssOptions,
    *,
    homepage: str,
    licence_note: str = OUTLET_NOTE,
    language: str = "en",
    flags: frozenset[str] = frozenset(),
) -> RssSeed:
    spec = SourceSpec(
        id=source_id,
        name=name,
        organisation=organisation,
        category=category,
        kind=SourceKind.RSS,
        url=url,
        reliability=reliability,
        poll_interval=timedelta(minutes=minutes),
        language=language,
        licence_note=licence_note,
        homepage=homepage,
        flags=flags,
    )
    return RssSeed(spec, options)


P, N, H = Category.POLITICAL, Category.NEWS, Category.HUMANITARIAN
A, B, C = Reliability.A, Reliability.B, Reliability.C

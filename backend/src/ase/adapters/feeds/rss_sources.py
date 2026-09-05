"""The seeded RSS and Atom sources: official feeds and outlets verified live on 5 September 2026.

Rows, not code: each seed is a SourceSpec plus the options that turn its items into
events. Grades follow docs/02_DATA_SOURCES.md (B for wires and public broadcasters, C
for national press, C with `state_controlled` for state media). Feeds that answered
404 or 403 to a polite fetch (Kyiv Independent, Focus Taiwan, NHK World, ISW, Kyodo)
are left out until their URLs are confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss import RssConnector, RssOptions
from ase.application.ports import Clock
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


def _seed(
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

RSS_SEEDS: tuple[RssSeed, ...] = (
    _seed(
        "gov_uk_fcdo_news",
        "GOV.UK FCDO news",
        "Foreign, Commonwealth and Development Office",
        P,
        "https://www.gov.uk/government/organisations/foreign-commonwealth-development-office.atom",
        B,
        30,
        OFFICIAL,
        homepage="https://www.gov.uk/government/organisations/foreign-commonwealth-development-office",
        licence_note=OGL,
    ),
    _seed(
        "gov_uk_travel_advice",
        "GOV.UK foreign travel advice",
        "Foreign, Commonwealth and Development Office",
        P,
        "https://www.gov.uk/foreign-travel-advice.atom",
        A,
        30,
        ADVISORY,
        homepage="https://www.gov.uk/foreign-travel-advice",
        licence_note=OGL,
    ),
    _seed(
        "us_state_travel_advisories",
        "US State Department travel advisories",
        "US Department of State",
        P,
        "https://travel.state.gov/_res/rss/TAsTWs.xml",
        A,
        60,
        US_ADVISORY,
        homepage="https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html",
        licence_note="US Government work",
    ),
    _seed(
        "un_news",
        "UN News",
        "United Nations",
        N,
        "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        B,
        30,
        RssOptions(
            tags=frozenset({"un"}),
            credibility=Credibility.PROBABLY_TRUE,
            rationale="UN news service report",
        ),
        homepage="https://news.un.org/",
        licence_note="UN terms of use",
    ),
    _seed(
        "un_press",
        "UN press releases and meetings coverage",
        "United Nations",
        P,
        "https://press.un.org/en/rss.xml",
        B,
        30,
        OFFICIAL,
        homepage="https://press.un.org/",
        licence_note="UN terms of use",
    ),
    _seed(
        "reliefweb_updates",
        "ReliefWeb updates",
        "UN OCHA ReliefWeb",
        H,
        "https://reliefweb.int/updates/rss.xml",
        B,
        30,
        RssOptions(
            subtype="report",
            tags=frozenset({"humanitarian"}),
            credibility=Credibility.PROBABLY_TRUE,
            rationale="Humanitarian report republished by ReliefWeb; source named in the item",
        ),
        homepage="https://reliefweb.int/",
        licence_note="Site CC BY 4.0; reports keep source copyright",
    ),
    _seed(
        "crisis_group",
        "International Crisis Group",
        "International Crisis Group",
        P,
        "https://www.crisisgroup.org/rss",
        B,
        60,
        RssOptions(
            subtype="analysis",
            tags=frozenset({"analysis"}),
            credibility=Credibility.PROBABLY_TRUE,
            rationale="Analysis by an established conflict-prevention organisation",
        ),
        homepage="https://www.crisisgroup.org/",
    ),
    _seed(
        "bbc_world",
        "BBC News World",
        "BBC",
        N,
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        B,
        15,
        WIRE,
        homepage="https://www.bbc.co.uk/news/world",
    ),
    _seed(
        "dw_world",
        "DW World",
        "Deutsche Welle",
        N,
        "https://rss.dw.com/rdf/rss-en-world",
        B,
        15,
        WIRE,
        homepage="https://www.dw.com/en/",
    ),
    _seed(
        "france24_en",
        "France 24 English",
        "France Médias Monde",
        N,
        "https://www.france24.com/en/rss",
        B,
        15,
        WIRE,
        homepage="https://www.france24.com/en/",
    ),
    _seed(
        "aljazeera_en",
        "Al Jazeera English",
        "Al Jazeera Media Network",
        N,
        "https://www.aljazeera.com/xml/rss/all.xml",
        B,
        15,
        WIRE,
        homepage="https://www.aljazeera.com/",
    ),
    _seed(
        "guardian_world",
        "The Guardian World",
        "Guardian Media Group",
        N,
        "https://www.theguardian.com/world/rss",
        C,
        15,
        PRESS,
        homepage="https://www.theguardian.com/world",
    ),
    _seed(
        "lemonde_en",
        "Le Monde in English",
        "Le Monde",
        N,
        "https://www.lemonde.fr/en/rss/une.xml",
        C,
        30,
        PRESS,
        homepage="https://www.lemonde.fr/en/",
    ),
    _seed(
        "scmp_news",
        "South China Morning Post",
        "SCMP",
        N,
        "https://www.scmp.com/rss/91/feed",
        C,
        30,
        PRESS,
        homepage="https://www.scmp.com/",
    ),
    _seed(
        "nikkei_asia",
        "Nikkei Asia",
        "Nikkei",
        N,
        "https://asia.nikkei.com/rss/feed/nar",
        C,
        30,
        PRESS,
        homepage="https://asia.nikkei.com/",
    ),
    _seed(
        "times_of_israel",
        "The Times of Israel",
        "The Times of Israel",
        N,
        "https://www.timesofisrael.com/feed/",
        C,
        15,
        PRESS,
        homepage="https://www.timesofisrael.com/",
    ),
    _seed(
        "anadolu_en",
        "Anadolu Agency English",
        "Anadolu Agency",
        N,
        "https://www.aa.com.tr/en/rss/default?cat=guncel",
        C,
        15,
        PRESS,
        homepage="https://www.aa.com.tr/en",
    ),
    _seed(
        "dawn",
        "Dawn",
        "Dawn Media Group",
        N,
        "https://www.dawn.com/feeds/home",
        C,
        30,
        PRESS,
        homepage="https://www.dawn.com/",
    ),
    _seed(
        "meduza_en",
        "Meduza in English",
        "Meduza",
        N,
        "https://meduza.io/rss/en/all",
        C,
        30,
        PRESS,
        homepage="https://meduza.io/en",
    ),
    _seed(
        "pravda_ua_en",
        "Ukrainska Pravda in English",
        "Ukrainska Pravda",
        N,
        "https://www.pravda.com.ua/eng/rss/",
        C,
        15,
        PRESS,
        homepage="https://www.pravda.com.ua/eng/",
    ),
    _seed(
        "tass_en",
        "TASS English",
        "TASS",
        N,
        "https://tass.com/rss/v2.xml",
        C,
        30,
        STATE_MEDIA,
        homepage="https://tass.com/",
        flags=frozenset({"state_controlled"}),
    ),
)


def build_rss_connectors(http: FeedHttpClient, clock: Clock) -> list[RssConnector]:
    return [RssConnector(http, clock, seed.spec, seed.options) for seed in RSS_SEEDS]

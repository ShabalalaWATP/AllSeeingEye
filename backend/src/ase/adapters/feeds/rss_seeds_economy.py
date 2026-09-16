"""Economic publisher and official-issuer feeds, each fetched live before registration.

Verified on 16 September 2026 with the application's own feed client: HTTP 200, a
well-formed feed, items dated within the preceding days, and a robots.txt that does not
restrict the path (an absent robots.txt is recorded as unrestricted). Rejected probes and
their reasons are listed in docs/02_DATA_SOURCES.md.

Primary directories: bankofengland.co.uk/rss, federalreserve.gov/feeds/feeds.htm,
ecb.europa.eu/rss, bis.org/cbspeeches, ons.gov.uk/releasecalendar, bls.gov/feed,
census.gov/economic-indicators, eia.gov/rss, boj.or.jp/en/rss, bankofcanada.ca/press,
rbi.org.in, wto.org/library/rss, cbr.ru/eng/about/rss, scmp.com/rss,
cgtn.com/subscribe/rss.html and tehrantimes.com/rss-help. Headlines and links only; all
sources remain F6.
"""

from dataclasses import replace

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.feeds.rss_seeds import OGL, RssSeed, seed
from ase.domain.events import Category, Credibility, Reliability

_BASE = RssOptions(
    tags=frozenset({"economic_news", "headlines_only"}),
    credibility=Credibility.CANNOT_BE_JUDGED,
    rationale="Publisher economic reporting; source reliability and claims remain unassessed.",
    headlines_only=True,
    newest_first=True,
)
_OFFICIAL = replace(
    _BASE,
    tags=_BASE.tags | {"official_issuer", "interested_party"},
    rationale="Official issuer statement, not independent verification of economic claims.",
)
_STATE = replace(
    _BASE,
    tags=_BASE.tags | {"state_aligned", "interested_party"},
    rationale="State-aligned publisher perspective; claims require independent corroboration.",
)
_TERMS = (
    "Publisher RSS terms apply. Headlines, dates, attribution and links only; no full article "
    "or imagery retained. Public feed access does not establish commercial reuse permission."
)
_US_PUBLIC = "US federal work, public domain; a User-Agent with contact is expected"
_ISSUER_TERMS = (
    "Issuer website terms apply. Headlines, dates, attribution and links only; no full "
    "release text retained."
)


def _row(
    key: str,
    name: str,
    organisation: str,
    url: str,
    homepage: str,
    options: RssOptions = _BASE,
    licence: str = _TERMS,
    minutes: int = 30,
) -> RssSeed:
    return seed(
        f"economic_{key}",
        name,
        organisation,
        Category.ECONOMIC,
        url,
        Reliability.F,
        minutes,
        options,
        homepage=homepage,
        licence_note=licence,
        flags=options.tags - {"economic_news", "headlines_only"},
    )


_ISSUERS: tuple[RssSeed, ...] = (
    _row(
        "bank_england",
        "Bank of England news",
        "Bank of England",
        "https://www.bankofengland.co.uk/rss/news",
        "https://www.bankofengland.co.uk/news",
        _OFFICIAL,
    ),
    _row(
        "hm_treasury",
        "HM Treasury announcements",
        "HM Treasury",
        "https://www.gov.uk/government/organisations/hm-treasury.atom",
        "https://www.gov.uk/government/organisations/hm-treasury",
        _OFFICIAL,
        OGL,
    ),
    _row(
        "ons_releases",
        "ONS statistical releases",
        "Office for National Statistics",
        "https://www.ons.gov.uk/releasecalendar?rss",
        "https://www.ons.gov.uk/releasecalendar",
        _OFFICIAL,
        OGL,
        60,
    ),
    _row(
        "federal_reserve",
        "Federal Reserve press releases",
        "US Federal Reserve",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        "https://www.federalreserve.gov/newsevents/pressreleases.htm",
        _OFFICIAL,
    ),
    _row(
        "bls_consumer_prices",
        "BLS consumer price index",
        "US Bureau of Labor Statistics",
        "https://www.bls.gov/feed/cpi.rss",
        "https://www.bls.gov/cpi/",
        _OFFICIAL,
        _US_PUBLIC,
        60,
    ),
    _row(
        "bls_employment",
        "BLS employment situation",
        "US Bureau of Labor Statistics",
        "https://www.bls.gov/feed/empsit.rss",
        "https://www.bls.gov/ces/",
        _OFFICIAL,
        _US_PUBLIC,
        60,
    ),
    _row(
        "bls_producer_prices",
        "BLS producer price index",
        "US Bureau of Labor Statistics",
        "https://www.bls.gov/feed/ppi.rss",
        "https://www.bls.gov/ppi/",
        _OFFICIAL,
        _US_PUBLIC,
        60,
    ),
    _row(
        "census_indicators",
        "US Census economic indicators",
        "US Census Bureau",
        "https://www.census.gov/economic-indicators/indicator.xml",
        "https://www.census.gov/economic-indicators/",
        _OFFICIAL,
        _US_PUBLIC,
        60,
    ),
    _row(
        "eia_energy",
        "EIA Today in Energy",
        "US Energy Information Administration",
        "https://www.eia.gov/rss/todayinenergy.xml",
        "https://www.eia.gov/todayinenergy/",
        _OFFICIAL,
        _US_PUBLIC,
        60,
    ),
    _row(
        "ecb_press",
        "European Central Bank press releases",
        "European Central Bank",
        "https://www.ecb.europa.eu/rss/press.html",
        "https://www.ecb.europa.eu/press/html/index.en.html",
        _OFFICIAL,
        _ISSUER_TERMS,
    ),
    _row(
        "bis_speeches",
        "BIS central bankers' speeches",
        "Bank for International Settlements",
        "https://www.bis.org/doclist/cbspeeches.rss",
        "https://www.bis.org/cbspeeches/",
        _OFFICIAL,
        _ISSUER_TERMS,
        60,
    ),
    _row(
        "wto_news",
        "WTO latest news",
        "World Trade Organization",
        "https://www.wto.org/library/rss/latest_news_e.xml",
        "https://www.wto.org/english/news_e/news_e.htm",
        _OFFICIAL,
        _ISSUER_TERMS,
        60,
    ),
    _row(
        "bank_japan",
        "Bank of Japan releases",
        "Bank of Japan",
        "https://www.boj.or.jp/en/rss/whatsnew.xml",
        "https://www.boj.or.jp/en/",
        _OFFICIAL,
        _ISSUER_TERMS,
        60,
    ),
    _row(
        "bank_canada",
        "Bank of Canada press releases",
        "Bank of Canada",
        "https://www.bankofcanada.ca/content_type/press-releases/feed/",
        "https://www.bankofcanada.ca/press/press-releases/",
        _OFFICIAL,
        _ISSUER_TERMS,
        60,
    ),
    _row(
        "reserve_bank_india",
        "Reserve Bank of India press releases",
        "Reserve Bank of India",
        "https://www.rbi.org.in/pressreleases_rss.xml",
        "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        _OFFICIAL,
        _ISSUER_TERMS,
        60,
    ),
    _row(
        "bank_russia",
        "Bank of Russia press releases",
        "Bank of Russia",
        "https://www.cbr.ru/rss/EngRssPress",
        "https://www.cbr.ru/eng/press/",
        _OFFICIAL,
    ),
)

_PUBLISHERS: tuple[RssSeed, ...] = (
    _row(
        "bbc_business",
        "BBC Business",
        "BBC",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.bbc.com/business",
    ),
    _row(
        "guardian_business",
        "The Guardian business",
        "Guardian Media Group",
        "https://www.theguardian.com/uk/business/rss",
        "https://www.theguardian.com/business",
    ),
    _row(
        "economist_finance",
        "The Economist finance and economics",
        "The Economist Group",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.economist.com/finance-and-economics",
    ),
    _row(
        "dw_business",
        "DW Business",
        "Deutsche Welle",
        "https://rss.dw.com/rdf/rss-en-bus",
        "https://www.dw.com/en/business/s-1431",
    ),
    _row(
        "france24_business",
        "France 24 Business",
        "France Medias Monde",
        "https://www.france24.com/en/business/rss",
        "https://www.france24.com/en/business/",
    ),
    _row(
        "intellinews",
        "bne IntelliNews",
        "Business New Europe",
        "https://www.intellinews.com/feed/",
        "https://www.intellinews.com/",
    ),
    _row(
        "the_bell",
        "The Bell",
        "The Bell",
        "https://en.thebell.io/feed/",
        "https://en.thebell.io/",
    ),
    _row(
        "scmp_china",
        "SCMP China economy",
        "SCMP",
        "https://www.scmp.com/rss/318421/feed/",
        "https://www.scmp.com/economy/china-economy",
    ),
    _row(
        "cgtn_business",
        "CGTN Business",
        "China Media Group",
        "https://www.cgtn.com/subscribe/rss/section/business.xml",
        "https://www.cgtn.com/business",
        _STATE,
    ),
    _row(
        "tehran_times",
        "Tehran Times economy",
        "Tehran Times",
        "https://www.tehrantimes.com/rss/tp/697",
        "https://www.tehrantimes.com/service/economy",
        _STATE,
    ),
)

ECONOMY_SEEDS: tuple[RssSeed, ...] = _ISSUERS + _PUBLISHERS

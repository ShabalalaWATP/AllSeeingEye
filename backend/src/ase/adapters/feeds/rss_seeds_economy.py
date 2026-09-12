"""Economic publisher feeds verified on 12 September 2026.

Primary directories: bankofengland.co.uk/rss, federalreserve.gov/feeds/feeds.htm,
cbr.ru/eng/about/rss, scmp.com/rss, cgtn.com/subscribe/rss.html and
tehrantimes.com/rss-help. Headlines and links only; all new sources remain F6.
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


def _row(
    key: str,
    name: str,
    organisation: str,
    url: str,
    homepage: str,
    options: RssOptions = _BASE,
    licence: str = _TERMS,
) -> RssSeed:
    return seed(
        f"economic_{key}",
        name,
        organisation,
        Category.ECONOMIC,
        url,
        Reliability.F,
        30,
        options,
        homepage=homepage,
        licence_note=licence,
        flags=options.tags - {"economic_news", "headlines_only"},
    )


ECONOMY_SEEDS: tuple[RssSeed, ...] = (
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
        "federal_reserve",
        "Federal Reserve press releases",
        "US Federal Reserve",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        "https://www.federalreserve.gov/newsevents/pressreleases.htm",
        _OFFICIAL,
    ),
    _row(
        "bank_russia",
        "Bank of Russia press releases",
        "Bank of Russia",
        "https://www.cbr.ru/rss/EngRssPress",
        "https://www.cbr.ru/eng/press/",
        _OFFICIAL,
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

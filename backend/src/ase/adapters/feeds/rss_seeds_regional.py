"""Publisher-discovered regional feeds, smoke-tested 6 September 2026.

Only titles, dates, attribution and source links enter the event store. Public RSS
availability is not a full-text republication licence or a credibility assessment.
Discovery, live probe results and limits: docs/SOURCE_FEASIBILITY_2026_09.md.
"""

from dataclasses import replace

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.feeds.rss_seeds import H, N, RssSeed, seed
from ase.domain.events import Credibility, Reliability

REGIONAL_NEWS = RssOptions(
    credibility=Credibility.CANNOT_BE_JUDGED,
    rationale="Publisher-attributed regional reporting; source and claim not yet assessed.",
    tags=frozenset({"regional_reporting", "headlines_only"}),
    headlines_only=True,
)
AGGREGATED = replace(
    REGIONAL_NEWS,
    tags=REGIONAL_NEWS.tags | {"aggregator"},
    rationale="CDT curates and republishes material; original reporting origins need review.",
)
HUMAN_RIGHTS = replace(
    REGIONAL_NEWS,
    tags=REGIONAL_NEWS.tags | {"human_rights", "ngo_reporting"},
    rationale="Human-rights organisation reporting; claims and upstream sources need review.",
)
IRANWIRE = replace(REGIONAL_NEWS, newest_first=True)
TERMS = (
    "Publisher-supplied public RSS; titles, attribution, dates and links only. "
    "No article text or imagery retained; broader reuse rights not established."
)

REGIONAL_SEEDS: tuple[RssSeed, ...] = (
    seed(
        "meduza_ru",
        "Meduza in Russian",
        "Meduza",
        N,
        "https://meduza.io/rss/all",
        Reliability.F,
        30,
        REGIONAL_NEWS,
        homepage="https://meduza.io/",
        language="ru",
        licence_note=TERMS,
    ),
    seed(
        "mediazona_ru",
        "Mediazona in Russian",
        "Mediazona",
        N,
        "https://zona.media/rss",
        Reliability.F,
        30,
        REGIONAL_NEWS,
        homepage="https://zona.media/",
        language="ru",
        licence_note=TERMS,
    ),
    seed(
        "insider_ru",
        "The Insider in Russian",
        "The Insider",
        N,
        "https://theins.ru/feed",
        Reliability.F,
        30,
        REGIONAL_NEWS,
        homepage="https://theins.ru/",
        language="ru",
        licence_note=TERMS,
    ),
    seed(
        "cdt_zh",
        "China Digital Times in Chinese",
        "China Digital Times",
        N,
        "https://feeds.feedburner.com/chinadigitaltimes/IyPt",
        Reliability.F,
        60,
        AGGREGATED,
        homepage="https://chinadigitaltimes.net/chinese/",
        language="zh",
        licence_note=TERMS,
        flags=frozenset({"aggregator"}),
    ),
    seed(
        "hrana_fa",
        "HRANA in Persian",
        "Human Rights Activists in Iran",
        H,
        "https://www.hra-news.org/feed/",
        Reliability.F,
        30,
        HUMAN_RIGHTS,
        homepage="https://www.hra-news.org/",
        language="fa",
        licence_note=TERMS,
        flags=frozenset({"ngo_reporting"}),
    ),
    seed(
        "hrana_en",
        "HRANA in English",
        "Human Rights Activists in Iran",
        H,
        "https://www.en-hrana.org/feed/",
        Reliability.F,
        60,
        HUMAN_RIGHTS,
        homepage="https://www.en-hrana.org/",
        licence_note=TERMS,
        flags=frozenset({"ngo_reporting"}),
    ),
    seed(
        "iranwire_fa",
        "IranWire in Persian",
        "IranWire",
        N,
        "https://iranwire.com/fa/feed/",
        Reliability.F,
        30,
        IRANWIRE,
        homepage="https://iranwire.com/fa/",
        language="fa",
        licence_note=TERMS,
    ),
    seed(
        "iranwire_en",
        "IranWire in English",
        "IranWire",
        N,
        "https://iranwire.com/en/feed/",
        Reliability.F,
        60,
        IRANWIRE,
        homepage="https://iranwire.com/en/",
        licence_note=TERMS,
    ),
)

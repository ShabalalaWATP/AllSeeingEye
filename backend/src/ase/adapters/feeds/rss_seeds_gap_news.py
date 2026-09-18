"""Coverage-gap publisher feeds, verified 15 September 2026, with declared languages.

United States desks, the Gulf and Arab region, Latin America, Africa, the Caucasus and
Central Asia, and Southeast Asia. Probes and exclusions: docs/NEWS_SOURCE_COVERAGE.md.
"""

from ase.adapters.feeds.rss_news_seed import news_seed
from ase.adapters.feeds.rss_seeds import RssSeed

GAP_NEWS_SEEDS: tuple[RssSeed, ...] = (
    news_seed(
        "cbs_world",
        "CBS News World",
        "CBS News",
        "https://www.cbsnews.com/latest/rss/world",
        "https://www.cbsnews.com/world/",
        "International reporting from a US broadcaster.",
    ),
    news_seed(
        "abc_us_international",
        "ABC News International",
        "ABC News",
        "https://abcnews.go.com/abcnews/internationalheadlines",
        "https://abcnews.go.com/International",
        "International headlines from a US broadcaster.",
    ),
    news_seed(
        "the_national_uae",
        "The National UAE",
        "International Media Investments",
        "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml",
        "https://www.thenationalnews.com/",
        "UAE, Gulf and international news from an Abu Dhabi-owned publisher.",
    ),
    news_seed(
        "arab_news",
        "Arab News",
        "Saudi Research and Media Group",
        "https://www.arabnews.com/rss.xml",
        "https://www.arabnews.com/",
        "Saudi, Gulf and Middle East news from a Saudi-owned publisher.",
    ),
    news_seed(
        "middle_east_eye",
        "Middle East Eye",
        "Middle East Eye",
        "https://www.middleeasteye.net/rss",
        "https://www.middleeasteye.net/",
        "Middle East and North Africa news from a London-based publisher.",
    ),
    news_seed(
        "mexico_news_daily",
        "Mexico News Daily",
        "Mexico News Daily",
        "https://mexiconewsdaily.com/feed/",
        "https://mexiconewsdaily.com/",
        "Mexican national news in English.",
    ),
    news_seed(
        "insight_crime",
        "InSight Crime",
        "InSight Crime",
        "https://insightcrime.org/feed/",
        "https://insightcrime.org/",
        "Organised crime and security reporting across Latin America and the Caribbean.",
    ),
    news_seed(
        "infobae",
        "Infobae",
        "Infobae",
        "https://www.infobae.com/arc/outboundfeeds/rss/",
        "https://www.infobae.com/",
        "Argentine, Latin American and international news in Spanish.",
        language="es",
    ),
    news_seed(
        "nation_kenya",
        "Nation Kenya",
        "Nation Media Group",
        "https://www.nation.africa/kenya/rss.xml",
        "https://nation.africa/kenya",
        "Kenyan and East African news; linked articles may be paywalled.",
    ),
    news_seed(
        "sabc_news",
        "SABC News",
        "South African Broadcasting Corporation",
        "https://www.sabcnews.com/sabcnews/feed/",
        "https://www.sabcnews.com/sabcnews/",
        "South African and African news from the public broadcaster.",
    ),
    news_seed(
        "radio_dabanga",
        "Radio Dabanga",
        "Radio Dabanga",
        "https://www.dabangasudan.org/en/feed",
        "https://www.dabangasudan.org/en",
        "Sudan reporting in English from a Netherlands-based outlet.",
    ),
    news_seed(
        "oc_media",
        "OC Media",
        "OC Media",
        "https://oc-media.org/feed/",
        "https://oc-media.org/",
        "South Caucasus and North Caucasus news.",
    ),
    news_seed(
        "times_central_asia",
        "The Times of Central Asia",
        "The Times of Central Asia",
        "https://timesca.com/feed/",
        "https://timesca.com/",
        "Central Asian regional news in English.",
    ),
    news_seed(
        "rappler",
        "Rappler",
        "Rappler",
        "https://www.rappler.com/feed/",
        "https://www.rappler.com/",
        "Philippine and Southeast Asian news.",
    ),
    news_seed(
        "the_diplomat",
        "The Diplomat",
        "Diplomat Media",
        "https://thediplomat.com/feed/",
        "https://thediplomat.com/",
        "Asia-Pacific politics and security; some linked articles may be paywalled.",
    ),
)

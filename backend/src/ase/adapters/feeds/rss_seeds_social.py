"""Social listening through feeds: outlet video channels and subreddit listings.

Outlet channels keep their outlet's reliability (the video is the outlet's own report);
subreddits sit at doctrine's floor until something corroborates a post. Both are Atom
feeds, so the RSS connector does the work.
"""

from __future__ import annotations

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.feeds.rss_seeds import RssSeed, seed
from ase.domain.events import Category, Credibility, Reliability

VIDEO = RssOptions(
    subtype="video",
    tags=frozenset({"youtube"}),
    rationale="Outlet video report, not yet corroborated",
)
POST = RssOptions(
    subtype="post",
    tags=frozenset({"reddit"}),
    credibility=Credibility.CANNOT_BE_JUDGED,
    rationale="Public forum post; not corroborated",
)
YOUTUBE_NOTE = "YouTube terms; titles and links only"
REDDIT_NOTE = (
    "Reddit terms; non-commercial use with a descriptive User-Agent; titles and links only"
)


def _channel(
    source_id: str, name: str, organisation: str, channel: str, reliability: Reliability
) -> RssSeed:
    return seed(
        source_id,
        f"{name} (YouTube)",
        organisation,
        Category.SOCIAL,
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}",
        reliability,
        30,
        VIDEO,
        homepage=f"https://www.youtube.com/channel/{channel}",
        licence_note=YOUTUBE_NOTE,
    )


def _subreddit(name: str, minutes: int = 15) -> RssSeed:
    return seed(
        f"reddit_{name.lower()}",
        f"r/{name} (Reddit)",
        "Reddit",
        Category.SOCIAL,
        f"https://www.reddit.com/r/{name}/new/.rss",
        Reliability.E,
        minutes,
        POST,
        homepage=f"https://www.reddit.com/r/{name}/",
        licence_note=REDDIT_NOTE,
    )


SOCIAL_SEEDS: list[RssSeed] = [
    _channel("yt_bbc_news", "BBC News", "BBC", "UC16niRr50-MSBwiO3YDb3RA", Reliability.B),
    _channel("yt_reuters", "Reuters", "Reuters", "UChqUTb7kYRX8-EiaN3XFrSQ", Reliability.B),
    _channel("yt_dw_news", "DW News", "Deutsche Welle", "UCknLrEdhRCp1aegoMqRaCZg", Reliability.C),
    _channel(
        "yt_al_jazeera",
        "Al Jazeera English",
        "Al Jazeera",
        "UCNye-wNBqNL5ZzHSJj3l8Bg",
        Reliability.C,
    ),
    _channel(
        "yt_france24",
        "FRANCE 24 English",
        "France Médias Monde",
        "UCQfwfsi5VrQ8yKZ-UWmAEFg",
        Reliability.C,
    ),
    _channel("yt_sky_news", "Sky News", "Sky", "UCoMdktPbSTixAyNGwb-UYkQ", Reliability.C),
    _subreddit("worldnews"),
    _subreddit("geopolitics", 30),
    _subreddit("UkrainianConflict", 30),
]

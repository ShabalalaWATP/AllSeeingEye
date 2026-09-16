"""The reviewed YouTube channels this deployment polls through the Data API v3.

Rows, not code. Each row carries the handle a reviewer can check by eye. Six broadcaster
rows also carry the channel ID that was already in this repository; the rest are resolved
from their handle by one `channels.list` call, which returns the uploads playlist in the
same unit. Handles were reviewed offline: no key exists on this machine, so none has been
confirmed against the live API. A handle that does not resolve fails that one source's
poll and shows in source health; it never affects another channel.

Topics follow what the operator asked to watch: the war in Ukraine, Russia, China and
Taiwan, the Middle East, finance, cyber, drones, defence analysis, and world leaders'
own official channels. Grading rules live beside the row type in `youtube_channels.py`.
"""

from __future__ import annotations

from ase.adapters.feeds.youtube_channels import MAX_CHANNELS, YouTubeChannel, channel
from ase.domain.events import Reliability

B, C, E = Reliability.B, Reliability.C, Reliability.E
CHANNELS: tuple[YouTubeChannel, ...] = (
    # The six broadcaster channels the retired Atom feeds carried, with their IDs.
    channel(
        "yt_bbc_news",
        "BBC News",
        "BBC",
        "@BBCNews",
        "world_news",
        B,
        channel_id="UC16niRr50-MSBwiO3YDb3RA",
    ),
    channel(
        "yt_reuters",
        "Reuters",
        "Reuters",
        "@Reuters",
        "world_news",
        B,
        channel_id="UChqUTb7kYRX8-EiaN3XFrSQ",
    ),
    channel(
        "yt_dw_news",
        "DW News",
        "Deutsche Welle",
        "@dwnews",
        "world_news",
        C,
        channel_id="UCknLrEdhRCp1aegoMqRaCZg",
    ),
    channel(
        "yt_al_jazeera",
        "Al Jazeera English",
        "Al Jazeera",
        "@AlJazeeraEnglish",
        "world_news middle_east",
        C,
        channel_id="UCNye-wNBqNL5ZzHSJj3l8Bg",
    ),
    channel(
        "yt_france24",
        "FRANCE 24 English",
        "France Médias Monde",
        "@FRANCE24English",
        "world_news",
        C,
        channel_id="UCQfwfsi5VrQ8yKZ-UWmAEFg",
    ),
    channel(
        "yt_sky_news",
        "Sky News",
        "Sky",
        "@SkyNews",
        "world_news",
        C,
        channel_id="UCoMdktPbSTixAyNGwb-UYkQ",
    ),
    # World reporting.
    channel("yt_ap", "Associated Press", "Associated Press", "@AssociatedPress", "world_news", B),
    channel(
        "yt_guardian", "The Guardian", "Guardian News & Media", "@guardiannews", "world_news", C
    ),
    channel("yt_euronews", "euronews", "Euronews", "@euronews", "world_news", C),
    channel("yt_pbs_newshour", "PBS NewsHour", "PBS", "@PBSNewsHour", "world_news", C),
    # Ukraine and Russia.
    channel(
        "yt_kyiv_independent",
        "The Kyiv Independent",
        "The Kyiv Independent",
        "@kyivindependent",
        "ukraine russia",
        C,
    ),
    channel(
        "yt_meduza",
        "Meduza",
        "Meduza",
        "@meduzaproject",
        "russia ukraine",
        C,
        language="ru",
    ),
    # China and Taiwan.
    channel(
        "yt_scmp",
        "South China Morning Post",
        "South China Morning Post",
        "@SouthChinaMorningPost",
        "china taiwan",
        C,
    ),
    channel(
        "yt_taiwan_plus",
        "TaiwanPlus News",
        "TaiwanPlus",
        "@TaiwanPlusNews",
        "taiwan china",
        C,
    ),
    channel(
        "yt_cgtn",
        "CGTN",
        "China Global Television Network",
        "@CGTN",
        "china taiwan",
        C,
        state_aligned=True,
    ),
    # Middle East.
    channel(
        "yt_middle_east_eye",
        "Middle East Eye",
        "Middle East Eye",
        "@MiddleEastEye",
        "middle_east",
        C,
    ),
    # Finance.
    channel("yt_cnbc", "CNBC", "CNBC", "@CNBC", "finance", C),
    channel(
        "yt_financial_times", "Financial Times", "Financial Times", "@FinancialTimes", "finance", C
    ),
    channel("yt_economist", "The Economist", "The Economist", "@TheEconomist", "finance", C),
    # Cyber: conference and community channels, graded at doctrine's floor.
    channel("yt_defcon", "DEF CON", "DEF CON", "@DEFCONConference", "cyber", E, kind="analysis"),
    channel(
        "yt_black_hat", "Black Hat", "Black Hat", "@BlackHatOfficialYT", "cyber", E, kind="analysis"
    ),
    # Defence analysis, including drone warfare.
    channel(
        "yt_perun",
        "Perun",
        "Perun",
        "@PerunAU",
        "defence_analysis drones ukraine",
        E,
        kind="analysis",
    ),
    channel(
        "yt_war_on_the_rocks",
        "War on the Rocks",
        "War on the Rocks",
        "@WarontheRocks",
        "defence_analysis drones",
        E,
        kind="analysis",
        # Resolved against the live API on 16 September 2026; the handle does not answer.
        channel_id="UCDHMiMRPcBujnVdAvgCD3dw",
    ),
    channel(
        "yt_chatham_house",
        "Chatham House",
        "Chatham House",
        "@ChathamHouse",
        "defence_analysis china russia",
        E,
        kind="analysis",
        # Resolved against the live API on 16 September 2026; the handle does not answer.
        channel_id="UCWrBgaGjj6k5ZrTxbZzd0Og",
    ),
    # World leaders and official channels.
    channel("yt_nato", "NATO", "NATO", "@NATO", "official defence_analysis", B, kind="official"),
    channel(
        "yt_white_house",
        "The White House",
        "The White House",
        "@WhiteHouse",
        "official",
        B,
        kind="official",
    ),
    channel(
        "yt_number_10",
        "Number10gov",
        "Prime Minister's Office, 10 Downing Street",
        "@10DowningStreet",
        "official",
        B,
        kind="official",
    ),
    channel(
        "yt_united_nations",
        "United Nations",
        "United Nations",
        "@unitednations",
        "official middle_east",
        B,
        kind="official",
    ),
    channel(
        "yt_european_commission",
        "European Commission",
        "European Commission",
        "@EuropeanCommission",
        "official finance",
        B,
        kind="official",
    ),
)


def load_channels() -> tuple[YouTubeChannel, ...]:
    """The packaged, reviewed channel list. A malformed row is a packaging fault."""
    if not CHANNELS or len(CHANNELS) > MAX_CHANNELS:
        raise ValueError(f"The YouTube channel list carries 1 to {MAX_CHANNELS} channels")
    for field in (
        [row.source_id for row in CHANNELS],
        [row.handle.lower() for row in CHANNELS],
        [row.channel_id for row in CHANNELS if row.channel_id],
    ):
        if len(set(field)) != len(field):
            raise ValueError("Each YouTube channel is listed once")
    return CHANNELS

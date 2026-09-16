"""Channels outside the Ukraine war: Middle East, Iran, Asia, Africa, cyber and markets.

Verified the same way as the war channels, on 16 September 2026. Telegram's coverage is
very uneven outside the Russian-speaking world: this file is short because most of the
obvious candidates either publish no public channel preview or had gone silent, and the
gaps are listed in ``docs/TELEGRAM_CHANNEL_COVERAGE.md`` rather than filled with an
unattributable aggregator.
"""

from __future__ import annotations

from ase.adapters.feeds.telegram_channel_registry import TelegramChannel, channel

MIDDLE_EAST: tuple[TelegramChannel, ...] = (
    channel(
        "idfofficial",
        "Israel Defense Forces",
        "Israel Defense Forces",
        "middle_east",
        "The Israeli military's own statements on strikes, operations and casualties, "
        "issued by a belligerent about its own operations.",
        "official_issuer",
        alignment="Israel",
        minutes=30,
    ),
    channel(
        "IsraelWarRoom",
        "Israel War Room",
        "Israel War Room, an Israeli advocacy media project",
        "middle_east",
        "Fast pro-Israel aggregation of strike and security claims; openly campaigning "
        "rather than reporting.",
        "aligned_commentator",
        alignment="Israel",
        minutes=120,
    ),
    channel(
        "QudsNen",
        "Quds News Network",
        "Quds News Network, a Palestinian media network",
        "middle_east",
        "Palestinian coverage of raids, strikes and casualties in Gaza and the West "
        "Bank, from the other side of the same events.",
        "aligned_commentator",
        alignment="Palestinian",
        minutes=60,
    ),
    channel(
        "PressTV",
        "Press TV",
        "Press TV, the English channel of Iranian state broadcaster IRIB",
        "middle_east",
        "Iranian state broadcasting in English; the Iranian government's framing of "
        "regional strikes, nuclear talks and sanctions.",
        "state_media",
        alignment="Iran",
        minutes=120,
    ),
    channel(
        "irna_1313",
        "IRNA",
        "Islamic Republic News Agency, the Iranian state news agency",
        "middle_east",
        "Iran's state wire in Persian, carrying official announcements before their "
        "English translations appear.",
        "state_media",
        alignment="Iran",
        language="fa",
        minutes=120,
    ),
)

WIDER_WORLD: tuple[TelegramChannel, ...] = (
    channel(
        "scmpnews",
        "South China Morning Post",
        "South China Morning Post, Hong Kong, owned by Alibaba Group",
        "asia_pacific",
        "The most consistent English coverage of China, Hong Kong and Taiwan tensions "
        "available on Telegram; ownership and jurisdiction are a constraint on it.",
        "publisher",
        minutes=60,
    ),
    channel(
        "Mali_Actu",
        "Mali Actu",
        "Mali Actu (maliactu.net), a Malian news outlet",
        "africa_sahel",
        "Malian outlet covering the Sahel insurgency, junta politics and Russian "
        "paramilitary activity; posts in bursts rather than daily.",
        "publisher",
        language="fr",
        minutes=240,
    ),
    channel(
        "OSINTdefender",
        "OSINTdefender",
        "OSINTdefender, an independent conflict-monitoring account",
        "conflict_monitoring",
        "High-tempo English aggregation of conflict claims worldwide; frequently first, "
        "and its early claims are often corrected afterwards.",
        "publisher",
        minutes=60,
    ),
    channel(
        "bloomberg",
        "Bloomberg",
        "Bloomberg L.P.",
        "finance_sanctions",
        "Markets, sanctions and energy headlines; the financial read on events the "
        "conflict channels cover first.",
        "publisher",
        minutes=120,
    ),
)

CYBER: tuple[TelegramChannel, ...] = (
    channel(
        "vxunderground",
        "vx-underground",
        "vx-underground, a malware research collective",
        "cyber_threat",
        "Ransomware group activity, leaks and malware research, usually posted here "
        "before it reaches vendor blogs.",
        "publisher",
        minutes=60,
    ),
    channel(
        "thehackernews",
        "The Hacker News",
        "The Hacker News",
        "cyber_threat",
        "Established security news outlet; vulnerability and intrusion coverage in "
        "step with vendor advisories.",
        "publisher",
        minutes=120,
    ),
    channel(
        "BleepingComputer",
        "BleepingComputer",
        "BleepingComputer",
        "cyber_threat",
        "Incident and ransomware reporting with technical detail, and the usual first "
        "confirmation of a named victim organisation.",
        "publisher",
        minutes=120,
    ),
    channel(
        "RedPacketSecurity",
        "RedPacket Security",
        "RedPacket Security",
        "cyber_threat",
        "Automated aggregation of advisories, breach claims and leak-site listings; "
        "volume rather than judgement.",
        "publisher",
        minutes=240,
    ),
)

WORLD_CHANNELS: tuple[TelegramChannel, ...] = (*MIDDLE_EAST, *WIDER_WORLD, *CYBER)

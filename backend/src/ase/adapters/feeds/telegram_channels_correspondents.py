"""War correspondents, milbloggers and mapping projects on both sides of the Ukraine war.

These are the fastest channels in the registry and the least checkable. Every one of them
is a participant: Ukrainian mapping projects and strategic-communications accounts, and
Russian milbloggers who are decorated, sourced inside their own armed forces, or employed
by the state broadcaster. They exist here to be read against each other, never alone.

Each entry was loaded and parsed from its public preview page on 16 September 2026 and had
posted within the preceding week unless noted. Channels dropped during that check are
recorded in ``docs/TELEGRAM_CHANNEL_COVERAGE.md`` rather than guessed at here."""

from __future__ import annotations

from ase.adapters.feeds.telegram_channel_registry import TelegramChannel, channel

UKRAINE_ALIGNED: tuple[TelegramChannel, ...] = (
    channel(
        "DeepStateUA",
        "DeepState",
        "DeepState, a Ukrainian volunteer mapping project",
        "conflict_monitoring",
        "The most-cited Ukrainian front-line mapping project; publishes claimed Russian "
        "advances hours before they are reported elsewhere, from the Ukrainian side.",
        "aligned_commentator",
        alignment="Ukraine",
        language="uk",
        minutes=30,
    ),
    channel(
        "Pravda_Gerashchenko",
        "Anton Gerashchenko",
        "Anton Gerashchenko, former adviser to Ukraine's Ministry of Internal Affairs",
        "conflict_monitoring",
        "High-volume Ukrainian strategic-communications account; fast, widely reposted "
        "and explicitly campaigning.",
        "aligned_commentator",
        alignment="Ukraine",
        minutes=120,
    ),
    channel(
        "Tsaplienko",
        "Andriy Tsaplienko",
        "Andriy Tsaplienko, Ukrainian war correspondent",
        "conflict_monitoring",
        "Established Ukrainian front-line correspondent; first-hand material from a "
        "participant, not an independent observer.",
        "aligned_commentator",
        alignment="Ukraine",
        language="uk",
        minutes=120,
    ),
    channel(
        "operativnoZSU",
        "Operatyvno ZSU",
        "Unattributed Ukrainian military-news aggregator",
        "conflict_monitoring",
        "Fast Ukrainian war aggregator often mistaken for a General Staff channel; it is "
        "not one, and the operator is not established.",
        "aligned_commentator",
        alignment="Ukraine",
        language="uk",
        minutes=120,
    ),
)

RUSSIA_MILBLOGGERS: tuple[TelegramChannel, ...] = (
    channel(
        "rybar",
        "Rybar",
        "Rybar, a Russian military analysis project",
        "russia_milblogger",
        "The most-cited Russian military mapping and analysis channel; well informed, "
        "reportedly founded by a former defence-ministry press officer, and an "
        "instrument of the Russian war effort.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=30,
    ),
    channel(
        "boris_rozhin",
        "Colonelcassad",
        "Boris Rozhin, a Russian military commentator",
        "russia_milblogger",
        "High-volume Russian war commentary and claimed front-line changes; a "
        "participant's account of a war he supports.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=30,
    ),
    channel(
        "wargonzo",
        "WarGonzo",
        "Semyon Pegov, a Russian war correspondent",
        "russia_milblogger",
        "Embedded Russian correspondent posting from occupied areas; first-hand, "
        "committed and state-decorated.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "epoddubny",
        "Yevgeny Poddubny",
        "Yevgeny Poddubny, war correspondent for the state broadcaster VGTRK",
        "russia_milblogger",
        "State television's front-line correspondent; his reporting is the state "
        "broadcast version of the war.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "sashakots",
        "Kotsnews",
        "Alexander Kots, correspondent for Komsomolskaya Pravda",
        "russia_milblogger",
        "Long-running Russian war correspondent with access to Russian units.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "dva_majors",
        "Dva Majora",
        "Dva Majora, an anonymous Russian military channel",
        "russia_milblogger",
        "Widely followed Russian front-line channel; anonymous, well sourced within "
        "Russian forces and openly partisan.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "milinfolive",
        "Voenny Osvedomitel",
        "Voenny Osvedomitel, a Russian military-technical channel",
        "russia_milblogger",
        "Equipment and drone identification from the Russian side; the usual first "
        "Russian source on new systems.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "RVvoenkor",
        "Rusvesna war correspondents",
        "Russkaya Vesna, a Russian nationalist outlet",
        "russia_milblogger",
        "High-tempo Russian claims of strikes and advances; nationalist outlet, "
        "frequently unverified.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "voenkorKotenok",
        "Yuri Kotenok",
        "Yuri Kotenok, a Russian war correspondent",
        "russia_milblogger",
        "Russian correspondent posting claimed strike results and front-line movement.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "SolovievLive",
        "Vladimir Solovyov",
        "Vladimir Solovyov, state television presenter",
        "russia_milblogger",
        "The clearest statement of Russian state television's line, useful as a "
        "narrative indicator rather than as reporting.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "intelslava",
        "Intel Slava Z",
        "Intel Slava Z, an English-language pro-Russian aggregator",
        "russia_milblogger",
        "The main English-language pipe for Russian war claims; carries state and "
        "milblogger material to foreign audiences, often without correction.",
        "state_media",
        alignment="Russia",
        minutes=120,
    ),
)

CORRESPONDENT_CHANNELS: tuple[TelegramChannel, ...] = (
    *UKRAINE_ALIGNED,
    *RUSSIA_MILBLOGGERS,
)

"""Russian official, state media and independent channels, kept apart on purpose.

Ministries and state agencies are the Russian state speaking for itself; the independent
and exiled outlets are not a counterweight to them, only a different unverified account,
and several publish under Russian wartime media law. All are graded at the same floor.

Each entry was loaded and parsed from its public preview page on 16 September 2026 and had
posted within the preceding week unless noted. Channels dropped during that check are
recorded in ``docs/TELEGRAM_CHANNEL_COVERAGE.md`` rather than guessed at here."""

from __future__ import annotations

from ase.adapters.feeds.telegram_channel_registry import TelegramChannel, channel

RUSSIA_OFFICIAL: tuple[TelegramChannel, ...] = (
    channel(
        "mod_russia",
        "Russian Ministry of Defence",
        "Ministry of Defence of the Russian Federation",
        "russia_official",
        "The Russian military's own daily briefings and claimed results, issued by a "
        "belligerent about its own war.",
        "official_issuer",
        alignment="Russia",
        language="ru",
        minutes=30,
    ),
    channel(
        "mod_russia_en",
        "Russian Ministry of Defence (English)",
        "Ministry of Defence of the Russian Federation",
        "russia_official",
        "English edition of the Russian MoD briefings, the version aimed at "
        "international audiences.",
        "official_issuer",
        alignment="Russia",
        minutes=30,
    ),
    channel(
        "MID_Russia",
        "Russian Ministry of Foreign Affairs",
        "Ministry of Foreign Affairs of the Russian Federation",
        "russia_official",
        "Russian diplomatic statements, sanctions responses and briefings in Russian.",
        "official_issuer",
        alignment="Russia",
        language="ru",
    ),
    channel(
        "MFARussia",
        "Russian MFA (English)",
        "Ministry of Foreign Affairs of the Russian Federation",
        "russia_official",
        "English-language Russian foreign ministry messaging, the text quoted abroad.",
        "official_issuer",
        alignment="Russia",
    ),
    channel(
        "mchs_official",
        "EMERCOM of Russia",
        "Ministry of Emergency Situations of the Russian Federation",
        "emergency_response",
        "Russian emergency service reporting on fires, floods and incident response, "
        "including strikes inside Russia.",
        "official_issuer",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "centralbank_russia",
        "Bank of Russia",
        "Central Bank of the Russian Federation",
        "finance_sanctions",
        "Rate decisions, capital controls and sanctions responses from the institution "
        "that issues them.",
        "official_issuer",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
)

RUSSIA_STATE_MEDIA: tuple[TelegramChannel, ...] = (
    channel(
        "rian_ru",
        "RIA Novosti",
        "Rossiya Segodnya, a Russian state media group",
        "russia_state_media",
        "State wire agency; the fastest carrier of Kremlin announcements and their framing.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=30,
    ),
    channel(
        "tass_agency",
        "TASS",
        "TASS, the Russian state news agency",
        "russia_state_media",
        "The state news agency of record; official statements in full, with state "
        "editorial direction.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=30,
    ),
    channel(
        "izvestia",
        "Izvestia",
        "Izvestia, part of the National Media Group",
        "russia_state_media",
        "Kremlin-aligned daily; carries defence and security briefings ahead of the "
        "official channels.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
    channel(
        "readovkanews",
        "Readovka",
        "Readovka, a pro-Kremlin Russian news outlet",
        "russia_state_media",
        "High-volume pro-government outlet used to test and spread official narratives.",
        "state_media",
        alignment="Russia",
        language="ru",
        minutes=120,
    ),
)

RUSSIA_INDEPENDENT: tuple[TelegramChannel, ...] = (
    channel(
        "meduzalive",
        "Meduza",
        "Meduza, an exiled Russian newsroom based in Latvia",
        "russia_independent",
        "Leading independent Russian-language newsroom, designated undesirable in "
        "Russia; reports what state media omits.",
        "publisher",
        language="ru",
        minutes=30,
    ),
    channel(
        "mediazzzona",
        "Mediazona",
        "Mediazona, an independent Russian outlet",
        "russia_independent",
        "Court, prison and casualty-verification reporting, including its named Russian "
        "military deaths count.",
        "publisher",
        language="ru",
        minutes=120,
    ),
    channel(
        "agentstvonews",
        "Agentstvo",
        "Agentstvo, an independent Russian investigative outlet",
        "russia_independent",
        "Investigative reporting on the Russian state and economy, largely from open "
        "Russian records.",
        "publisher",
        language="ru",
        minutes=120,
    ),
    channel(
        "astrapress",
        "ASTRA",
        "ASTRA, an independent Russian journalists' collective",
        "russia_independent",
        "Incident reporting from inside Russia, including drone strikes and refinery "
        "fires the authorities do not confirm.",
        "publisher",
        language="ru",
        minutes=60,
    ),
    channel(
        "ostorozhno_novosti",
        "Ostorozhno Novosti",
        "Ostorozhno Novosti, an independent Russian outlet",
        "russia_independent",
        "Fast independent Russian breaking news, including incidents inside Russia.",
        "publisher",
        language="ru",
        minutes=120,
    ),
    channel(
        "bazabazon",
        "Baza",
        "Baza, a Russian incident-news outlet",
        "russia_independent",
        "First Russian source on many domestic incidents; its reported security-services "
        "sourcing is a bias as well as an advantage.",
        "publisher",
        language="ru",
        minutes=120,
    ),
    channel(
        "shot_shot",
        "SHOT",
        "SHOT, a Russian incident-news outlet",
        "russia_independent",
        "High-tempo Russian incident reporting, including drone attacks inside Russia; "
        "frequently first and frequently wrong.",
        "publisher",
        language="ru",
        minutes=120,
    ),
    channel(
        "rbc_news",
        "RBC",
        "RBC, a Russian business media group",
        "russia_independent",
        "Russian business and economic reporting on sanctions, budget and industry, "
        "published under Russian wartime media restrictions.",
        "publisher",
        language="ru",
        minutes=120,
    ),
    channel(
        "kommersant",
        "Kommersant",
        "Kommersant, a Russian business daily",
        "russia_independent",
        "Established Russian business daily; defence-industrial and economic detail, "
        "published under Russian wartime media restrictions.",
        "publisher",
        language="ru",
        minutes=120,
    ),
)

RUSSIA_CHANNELS: tuple[TelegramChannel, ...] = (
    *RUSSIA_OFFICIAL,
    *RUSSIA_STATE_MEDIA,
    *RUSSIA_INDEPENDENT,
)

"""Ukrainian official and media channels. Ukraine is a belligerent, so none of these is an
observer: an institution's own channel is graded as an interested party speaking for
itself, and the state agency and public broadcaster are marked state-aligned.

Each entry was loaded and parsed from its public preview page on 16 September 2026 and had
posted within the preceding week unless noted. Channels dropped during that check are
recorded in ``docs/TELEGRAM_CHANNEL_COVERAGE.md`` rather than guessed at here."""

from __future__ import annotations

from ase.adapters.feeds.telegram_channel_registry import TelegramChannel, channel

UKRAINE_OFFICIAL: tuple[TelegramChannel, ...] = (
    channel(
        "V_Zelenskiy_official",
        "Volodymyr Zelenskyy",
        "Office of the President of Ukraine",
        "ukraine_official",
        "The president's own channel: addresses, decrees and strike reactions, usually "
        "ahead of the presidential website.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
        minutes=30,
    ),
    channel(
        "generalstaffZSU",
        "General Staff of the Armed Forces of Ukraine",
        "General Staff of the Armed Forces of Ukraine",
        "ukraine_official",
        "Daily operational reports and claimed Russian losses, issued by a belligerent "
        "about its own war.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
        minutes=30,
    ),
    channel(
        "kpszsu",
        "Air Force Command of the Armed Forces of Ukraine",
        "Air Force Command of the Armed Forces of Ukraine",
        "ukraine_official",
        "Missile and drone warnings and post-strike interception counts, the fastest "
        "official record of a Russian air attack.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
        minutes=30,
    ),
    channel(
        "mvs_ukraine",
        "Ministry of Internal Affairs of Ukraine",
        "Ministry of Internal Affairs of Ukraine",
        "ukraine_official",
        "Police, border and internal-security statements, including casualty figures "
        "after strikes on civilian areas.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
    ),
    channel(
        "dsns_telegram",
        "State Emergency Service of Ukraine",
        "State Emergency Service of Ukraine (DSNS)",
        "emergency_response",
        "The rescue service's own record of fires, rubble clearance and casualties after "
        "strikes, published before official statistics.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
    ),
    channel(
        "ukrenergo",
        "Ukrenergo",
        "NPC Ukrenergo, the Ukrainian transmission system operator",
        "ukraine_official",
        "Grid damage, emergency load shedding and repair status after strikes on the "
        "power system, from the operator itself.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
    ),
    channel(
        "nbu_ua",
        "National Bank of Ukraine",
        "National Bank of Ukraine",
        "finance_sanctions",
        "Central bank decisions, reserves and wartime currency controls, issued by the "
        "authority that sets them.",
        "official_issuer",
        alignment="Ukraine",
        language="uk",
        minutes=120,
    ),
)

UKRAINE_MEDIA: tuple[TelegramChannel, ...] = (
    channel(
        "ukrinform_news",
        "Ukrinform",
        "Ukrinform, the Ukrainian state news agency",
        "ukraine_media",
        "The state agency's wire, carrying official announcements quickly and reflecting "
        "the government's framing of them.",
        "state_media",
        alignment="Ukraine",
        language="uk",
    ),
    channel(
        "suspilnenews",
        "Suspilne News",
        "Suspilne, Ukraine's public service broadcaster",
        "ukraine_media",
        "Public broadcaster newsroom with regional correspondents; state funded, with "
        "editorial independence in statute rather than in evidence.",
        "state_media",
        alignment="Ukraine",
        language="uk",
    ),
    channel(
        "UkraineNow",
        "Ukraine NOW",
        "Ukrainian government information channel",
        "ukraine_media",
        "Government-run public information channel used for air alerts, evacuation and "
        "official messaging; a party's own communication.",
        "state_media",
        alignment="Ukraine",
        language="uk",
    ),
    channel(
        "United24media",
        "UNITED24 Media",
        "UNITED24, the Ukrainian government fundraising and media platform",
        "ukraine_media",
        "English-language output of a Ukrainian state platform whose purpose is raising "
        "support; useful and openly advocacy.",
        "state_media",
        alignment="Ukraine",
        minutes=120,
    ),
    channel(
        "ukrpravda_news",
        "Ukrainska Pravda",
        "Ukrainska Pravda",
        "ukraine_media",
        "Long-established independent Ukrainian outlet; breaks political and procurement "
        "stories the state channels do not carry.",
        "publisher",
        language="uk",
    ),
    channel(
        "nvua_official",
        "NV",
        "NV (Novoye Vremya)",
        "ukraine_media",
        "Independent Ukrainian newsroom with fast war coverage in Ukrainian and Russian.",
        "publisher",
        language="uk",
        minutes=120,
    ),
    channel(
        "kyivindependent_official",
        "The Kyiv Independent",
        "The Kyiv Independent",
        "ukraine_media",
        "Independent English-language Ukrainian newsroom; the usual English entry point "
        "for Ukrainian reporting.",
        "publisher",
    ),
    channel(
        "radiosvoboda",
        "Radio Svoboda",
        "Radio Free Europe/Radio Liberty, funded by the United States Congress",
        "ukraine_media",
        "RFE/RL Russian-language service covering Ukraine and Russia; independent "
        "newsroom under US government funding.",
        "state_media",
        alignment="United States",
        language="ru",
        minutes=120,
    ),
    channel(
        "nexta_live",
        "NEXTA",
        "NEXTA, a Belarusian opposition outlet based in Poland",
        "ukraine_media",
        "Belarusian opposition channel covering Belarus, Russia and the war; openly "
        "campaigning against both governments.",
        "aligned_commentator",
        alignment="Belarusian opposition",
        language="ru",
        minutes=120,
    ),
    channel(
        "minfin_news",
        "Minfin",
        "minfin.com.ua, a Ukrainian financial portal",
        "finance_sanctions",
        "Ukrainian exchange rates, banking and budget coverage during capital controls "
        "and wartime finance.",
        "publisher",
        language="ru",
        minutes=120,
    ),
)

UKRAINE_CHANNELS: tuple[TelegramChannel, ...] = (
    *UKRAINE_OFFICIAL,
    *UKRAINE_MEDIA,
)

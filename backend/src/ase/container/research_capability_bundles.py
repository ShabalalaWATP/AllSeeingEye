"""Preset bundle building blocks. Missing bridges are disclosure records, never provider IDs."""

from ase.domain.source_capabilities import (
    CapabilityRef,
    GapRef,
    SourceBundle,
    SourceCapability,
    UnavailableCapabilityGap,
)


def capability_gaps() -> tuple[UnavailableCapabilityGap, ...]:
    entries = (
        (
            "original_passages",
            "Permitted original news passages",
            "Automatic admitted discovery-to-original retrieval is E02 work; current RSS routes "
            "retain headline metadata. Separate selected imports do not make RSS full text.",
        ),
        (
            "additional_news_feeds",
            "Additional dashboard news publishers",
            "Dashboard News seeds outside the current research publisher registry have no private "
            "headline research route. Precise retained area items remain conditional on the cache.",
        ),
        (
            "official_routes",
            "Additional official diplomatic and government routes",
            "Only registered feeds and Parliament questions are executable; "
            "further routes require E03.",
        ),
        (
            "conflict_records",
            "Structured conflict research beyond retained area items",
            "ACLED, UCDP and GDELT dashboard access does not establish a private research "
            "bridge. Existing precise retained area items are bounded by cache coverage.",
        ),
        (
            "humanitarian_records",
            "Structured humanitarian research",
            "ReliefWeb API and IFRC dashboard adapters are not private research providers; "
            "ReliefWeb RSS headlines remain available through the registered publisher route.",
        ),
        (
            "cti_kev",
            "Known exploited vulnerability records",
            "Current CISA KEV dashboard records have no typed private research provider bridge.",
        ),
        (
            "cti_actor_reference",
            "ATT&CK actor reference background",
            "Packaged ATT&CK groups are historical reference context, not a current-news research "
            "provider. A typed evidence bridge is still required.",
        ),
        (
            "network_telemetry",
            "Additional network telemetry and history",
            "Radar layer3/layer7 current target-country distributions have explicit licensed "
            "research routes. IODA country event windows have a separate opt-in research "
            "route, pending operator data-use review. Cloudflare outage annotations and "
            "complete network history remain unavailable as research routes; none of these "
            "signals establishes cause or incident attribution.",
        ),
        (
            "ons_ecb",
            "Additional ONS and ECB statistical research",
            "UK CPIH supports one explicit version and at most 24 monthly observations. "
            "ECB supports one explicit daily GBP-per-EUR reference-rate series. "
            "Latest-version discovery, other ONS and ECB series remain unavailable; "
            "official headlines do not provide additional statistical series or vintages.",
        ),
        (
            "macro_series",
            "Additional macroeconomic series and vintages",
            "World Bank annual indicators are supported; dashboard series and IMF/OECD sources "
            "outside that exact route need typed research bridges and vintage disclosures.",
        ),
        (
            "trade_shipping",
            "Trade and shipping research records",
            "Corporate, sanctions and procurement routes do not establish trade-flow or shipping "
            "history. Dedicated typed research bridges remain unavailable.",
        ),
        (
            "energy_statistics",
            "Structured energy statistics",
            "Economic headlines and filings are context; dedicated energy series research and "
            "revision-aware records are not implemented.",
        ),
        (
            "mobility_history",
            "Mobility records beyond retained precise area observations",
            "No general private AIS, aviation or ports history provider exists. Current retained "
            "area evidence depends on feed configuration, precision, retention and admission.",
        ),
        (
            "hazard_history",
            "Additional hazard and weather history",
            "Area hazard routes and retained items are bounded; they do not provide full FIRMS, "
            "weather or country-wide historical research coverage.",
        ),
        (
            "scholarly_passages",
            "Permitted scholarly original passages",
            "OpenAlex and Crossref provide metadata; automatic paper acquisition is absent.",
        ),
        (
            "area_history",
            "Complete historical area coverage",
            "Retained precise points and bounded catalogue queries do not establish complete AOI "
            "history. Country-only records must remain separately labelled context.",
        ),
    )
    related = {
        "cti_kev": ("cisa_kev",),
        "cti_actor_reference": ("mitre_attack",),
        "network_telemetry": ("ioda_outage_events", "cloudflare_radar_outages"),
    }
    return tuple(
        UnavailableCapabilityGap(f"gap.{key}", name, reason, related.get(key, ()))
        for key, name, reason in entries
    )


def capability_bundles(capabilities: tuple[SourceCapability, ...]) -> tuple[SourceBundle, ...]:
    def families(*names: str) -> tuple[str, ...]:
        return tuple(row.id for row in capabilities if row.family in names)

    news = families("news_discovery", "outlet", "regional")
    official = families("official")
    humanitarian = tuple(
        row.id
        for row in capabilities
        if row.id.endswith(("reliefweb_updates", "un_news", "un_press", "hrana_en", "hrana_fa"))
    )
    economic = families("economy_news", "macro")
    corporate = families("corporate", "sanctions", "procurement", "development")
    area = ("research-retained-area-feeds",)
    entries = (
        ("NEWS", "News discovery", news, ("original_passages", "additional_news_feeds")),
        ("OFFICIAL", "Official publications", official, ("official_routes", "original_passages")),
        (
            "CONFLICT",
            "Conflict and security",
            news + official + humanitarian + area,
            ("conflict_records", "original_passages"),
        ),
        (
            "HUMANITARIAN",
            "Humanitarian reporting",
            humanitarian + area,
            ("humanitarian_records", "original_passages"),
        ),
        (
            "CTI",
            "Cyber threat intelligence",
            families("cyber_news", "technical", "network"),
            ("cti_kev", "cti_actor_reference", "original_passages"),
        ),
        ("NETWORK", "Network observations", families("network"), ("network_telemetry",)),
        ("MACRO", "Macroeconomic reporting", economic, ("ons_ecb", "macro_series")),
        (
            "TRADE",
            "Trade, corporate and sanctions records",
            corporate + economic,
            ("trade_shipping",),
        ),
        (
            "ENERGY",
            "Energy reporting and corporate context",
            economic + families("corporate"),
            ("energy_statistics",),
        ),
        ("MOBILITY", "Mobility observations", area, ("mobility_history",)),
        (
            "HAZARD",
            "Hazard observations",
            families("hazard", "environment") + humanitarian + area,
            ("hazard_history",),
        ),
        ("SCHOLARLY", "Scholarly discovery", families("scholarly"), ("scholarly_passages",)),
        (
            "AREA",
            "Area observations",
            area + families("hazard", "environment", "space", "development"),
            ("area_history",),
        ),
    )
    return tuple(
        SourceBundle(
            key,
            name,
            tuple(CapabilityRef(id_) for id_ in dict.fromkeys(ids))
            + tuple(GapRef(f"gap.{gap}") for gap in gaps),
        )
        for key, name, ids, gaps in entries
    )

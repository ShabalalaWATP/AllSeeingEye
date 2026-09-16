"""Compose the E00 inventory from reviewed executable routes without constructing collectors."""

from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.feeds.rss_seeds_economy import ECONOMY_SEEDS
from ase.adapters.feeds.rss_seeds_official import OFFICIAL_SEEDS
from ase.adapters.feeds.rss_seeds_outlets import OUTLET_SEEDS
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.news import EDITIONS
from ase.adapters.research.regional import LANGUAGE_ALIASES, REGIONAL_COUNTRIES
from ase.application.source_capabilities import SourceCapabilityRegistry
from ase.container.research_capability_bundles import capability_bundles, capability_gaps
from ase.container.research_capability_profiles import structured_profiles
from ase.container.research_sources import research_source_specs
from ase.domain.source_capabilities import (
    CapabilityScope as Scope,
)
from ase.domain.source_capabilities import (
    CapabilitySupport,
    SourceCapability,
)
from ase.domain.source_capabilities import (
    ContentCapability as Content,
)
from ase.domain.source_capabilities import (
    DateSupport as Dates,
)
from ase.domain.source_capabilities import (
    ExecutionRoute as Route,
)
from ase.domain.source_capabilities import (
    LanguageSupport as Language,
)
from ase.domain.sources import SourceSpec


def _feed_capabilities(specs: dict[str, SourceSpec]) -> list[SourceCapability]:
    result: list[SourceCapability] = []
    for language in EDITIONS:
        spec = specs[f"research_google_news_{language}"]
        result.append(
            SourceCapability(
                spec.id,
                spec.name,
                "news_discovery",
                Route.PUBLIC_RESEARCH,
                Content.DISCOVERY,
                CapabilitySupport(
                    (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
                    (Dates.PUBLICATION_INTERVAL,),
                    (language,),
                    Language.CONFIGURED,
                    "Explicit bounded phrases and configured edition; edition is not verified "
                    "article language or geography. Date-filtered RSS search, "
                    "no archive guarantee.",
                ),
                None,
                _limitations(spec),
                control_ids=("google_news", "google_news_watchlists"),
            )
        )
    groups = (
        ("official", "research_publisher_", OFFICIAL_SEEDS),
        ("outlet", "research_publisher_", OUTLET_SEEDS),
        ("economy_news", "research_publisher_", ECONOMY_SEEDS),
        ("cyber_news", "research_publisher_", CYBER_SEEDS),
        ("regional", "research_regional_", REGIONAL_SEEDS),
    )
    for family, prefix, seeds in groups:
        for seed in seeds:
            original = seed.spec
            spec = specs[f"{prefix}{original.id}"]
            languages = (
                tuple(
                    sorted(LANGUAGE_ALIASES.get(original.language, frozenset({original.language})))
                )
                if family == "regional"
                else (original.language,)
            )
            constraints = (
                "Bounded local headline phrase matching in a recent feed snapshot and publication "
                "interval; no original articles, historical archive or precise area support."
            )
            if family == "regional":
                constraints += (
                    f" Regional country selection {REGIONAL_COUNTRIES[original.id]} or explicit "
                    "source override routes this feed; neither establishes incident geography."
                )
            unknown_origin = original.id in {"cdt_zh", "reliefweb_updates"}
            result.append(
                SourceCapability(
                    spec.id,
                    spec.name,
                    family,
                    Route.PUBLIC_RESEARCH,
                    Content.DISCOVERY,
                    CapabilitySupport(
                        (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
                        (Dates.PUBLICATION_INTERVAL,),
                        languages,
                        Language.CONFIGURED,
                        constraints,
                    ),
                    None if unknown_origin else original.independence_key,
                    _limitations(spec),
                )
            )
    return result


def _limitations(spec: SourceSpec) -> tuple[str, ...]:
    if spec.rating is None:
        raise ValueError("Capability source requires explicit rating limitations")
    return (
        "Catalogue capability only; service availability and returned evidence have not been "
        "verified by this inventory. Origin groups are not independent corroboration.",
        *spec.rating.limitations,
    )


def research_capability_registry() -> SourceCapabilityRegistry:
    """No settings, credentials, local datasets, collector instances or live calls are read.

    Include disabled routes in the static catalogue so resolution can disclose exclusions.
    Existing source inventory requirement metadata may be supplied to resolve at request time.
    """
    specs = {spec.id: spec for spec in research_source_specs()}
    profiles = structured_profiles()
    capabilities = _feed_capabilities(specs)
    for source_id, profile in profiles.items():
        spec = specs[source_id]
        capabilities.append(
            SourceCapability(
                spec.id,
                spec.name,
                profile.family,
                profile.route,
                profile.content,
                profile.support,
                None if profile.unknown_origin or not spec.organisation else spec.independence_key,
                _limitations(spec),
                profile.prerequisites,
            )
        )
    if {row.id for row in capabilities} != set(specs):
        raise ValueError("Research catalogue changed without a reviewed capability profile")
    frozen = tuple(sorted(capabilities, key=lambda row: row.id))
    return SourceCapabilityRegistry(frozen, capability_gaps(), capability_bundles(frozen))

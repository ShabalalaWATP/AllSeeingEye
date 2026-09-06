"""Validate operator choices against the concrete provider inventory before collection."""

from collections.abc import Sequence
from dataclasses import replace

from ase.application.ports.research import ResearchProvider
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchQuery
from ase.domain.research_plan import (
    UNKNOWN_TEMPORAL_SCOPE,
    QueryVariant,
    ResearchPlan,
    ResearchTask,
)


def task_variant(
    query: ResearchQuery, language: str | None, aliases: tuple[str, ...]
) -> QueryVariant | None:
    for variant in query.query_variants:
        if language is not None and variant.language.lower() == language.lower():
            return variant
    matches = [variant for variant in query.query_variants if variant.language.lower() in aliases]
    if len(matches) > 1:
        raise InvalidRequest(
            "Multiple query variants match one source. Supply one compatible variant."
        )
    return matches[0] if matches else None


def build_plan(
    query: ResearchQuery,
    providers: Sequence[ResearchProvider],
    *,
    requests: int,
    seconds: float,
    items: int,
) -> ResearchPlan:
    inventory = {provider.id for provider in providers}
    if query.source_ids is not None and not set(query.source_ids).issubset(inventory):
        raise InvalidRequest(
            "Selected sources are unavailable for this research scope. Preview the plan again."
        )
    tasks = []
    for provider in providers:
        language = getattr(provider, "language", None)
        language = language if isinstance(language, str) else None
        aliases = getattr(provider, "query_language_aliases", ())
        aliases = tuple(value.lower() for value in aliases if isinstance(value, str))
        variant = task_variant(query, language, aliases)
        routed = replace(query, terms=variant.terms) if variant is not None else query
        provenance = "operator_supplied_variant" if routed is not query else "original_terms"
        temporal_scope = getattr(provider, "temporal_scope", UNKNOWN_TEMPORAL_SCOPE)
        if not isinstance(temporal_scope, str) or not temporal_scope or len(temporal_scope) > 1000:
            temporal_scope = UNKNOWN_TEMPORAL_SCOPE
        tasks.append(
            ResearchTask(
                provider.id,
                provider.name,
                query.source_ids is None or provider.id in query.source_ids,
                provider.supports(routed),
                language,
                routed.terms,
                provenance,
                temporal_scope,
                query_language=variant.language if variant is not None else None,
            )
        )
    return ResearchPlan(
        query.question,
        query.since,
        query.until,
        query.languages,
        tuple(tasks),
        requests,
        seconds,
        items,
        focus=query.focus.value,
        mode=query.mode.value,
        subject=query.subject,
        country_iso=query.country_iso,
    )

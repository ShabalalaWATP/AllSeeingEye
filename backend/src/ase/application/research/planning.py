"""Validate operator choices against the concrete provider inventory before collection."""

from collections.abc import Sequence
from dataclasses import replace

from ase.application.ports.research import ResearchProvider
from ase.application.research.registry_routing import (
    lookup_options,
    resolve_lookup,
    supports_lookup,
)
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchQuery
from ase.domain.research_plan import (
    UNKNOWN_SPATIAL_SCOPE,
    UNKNOWN_TEMPORAL_SCOPE,
    QueryVariant,
    ResearchPlan,
    ResearchTask,
)
from ase.domain.research_tasks import task_identity


def spatial_capability(provider: ResearchProvider, query: ResearchQuery) -> tuple[bool, str]:
    """Only an explicit synchronous true result admits an area-scoped request.

    The optional supports_area(query) hook is independent of ordinary country or
    subject support. Legacy providers remain usable without an area, never with one.
    """
    supports = getattr(provider, "supports_area", None)
    supported = False
    if query.area is not None and callable(supports):
        try:
            supported = supports(query) is True
        except Exception:
            supported = False
    explanation = getattr(provider, "spatial_scope", UNKNOWN_SPATIAL_SCOPE)
    if not isinstance(explanation, str) or not explanation.strip() or len(explanation) > 1000:
        explanation = UNKNOWN_SPATIAL_SCOPE
    return supported, explanation


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
    if any(task.source_id not in inventory for task in query.planned_tasks):
        raise InvalidRequest("Planned task source is unavailable for this research scope")
    if len(providers) + len(query.planned_tasks) > 64:
        raise InvalidRequest("Expanded research plans support at most 64 tasks")
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
        spatial_supported, spatial_scope = spatial_capability(provider, routed)
        tasks.append(
            ResearchTask(
                provider.id,
                provider.name,
                query.source_ids is None or provider.id in query.source_ids,
                provider.supports(routed) and (query.area is None or spatial_supported),
                language,
                routed.terms,
                provenance,
                temporal_scope,
                query_language=variant.language if variant is not None else None,
                spatial_supported=spatial_supported,
                spatial_scope=spatial_scope,
                task_id="source:" + provider.id,
                planned_terms_supported=getattr(provider, "supports_planned_terms", False) is True,
                registry_namespaces=getattr(provider, "registry_namespaces", ()),
                registry_options=lookup_options(provider, query),
            )
        )
    supplementary = []
    baseline = {task.source_id: task for task in tasks}
    by_id = {provider.id: provider for provider in providers}
    for operator in query.planned_tasks:
        lookup = resolve_lookup(query, operator)
        routed = replace(
            query,
            terms=operator.terms,
            query_variants=(),
            subject=lookup.subject if lookup else query.subject,
        )
        provider = by_id[operator.source_id]
        spatial_supported, spatial_scope = spatial_capability(provider, routed)
        supplementary.append(
            replace(
                baseline[operator.source_id],
                terms=operator.terms,
                supported=(
                    supports_lookup(provider, query, lookup)
                    if lookup
                    else baseline[operator.source_id].planned_terms_supported
                )
                and provider.supports(routed)
                and (query.area is None or spatial_supported),
                provenance="model_proposed_task"
                if operator.origin == "model"
                else "operator_supplied_task",
                query_language=None,
                spatial_supported=spatial_supported,
                spatial_scope=spatial_scope,
                task_id=task_identity(operator),
                purpose=operator.purpose,
                candidate_id=operator.candidate_id,
                registry_lookup=lookup,
            )
        )
    # Alternate baseline and explicit tasks so the latter do not sit behind the
    # full provider inventory. Every task still consumes the same run allowance.
    ordered = []
    selected = [task for task in tasks if task.selected]
    for index in range(max(len(selected), len(supplementary))):
        if index < len(selected):
            ordered.append(selected[index])
        if index < len(supplementary):
            ordered.append(supplementary[index])
    ordered.extend(task for task in tasks if not task.selected)
    return ResearchPlan(
        query.question,
        query.since,
        query.until,
        query.languages,
        tuple(ordered if supplementary else tasks),
        requests,
        seconds,
        items,
        focus=query.focus.value,
        mode=query.mode.value,
        subject=query.subject,
        country_iso=query.country_iso,
        area=query.area,
        time_basis=query.effective_time_basis,
        candidate_hypotheses=query.candidate_hypotheses,
    )

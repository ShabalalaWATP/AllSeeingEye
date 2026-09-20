"""Validate operator choices against the concrete provider inventory before collection."""

from collections.abc import Sequence
from dataclasses import replace

from ase.application.ports.research import ResearchProvider
from ase.application.ports.research_capabilities import AreaResearchProvider
from ase.application.research.provider_capabilities import provider_capabilities
from ase.application.research.registry_routing import (
    lookup_options,
    resolve_lookup,
    supports_lookup,
)
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchQuery
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS, MAX_PLAN_TASKS
from ase.domain.research_plan import (
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
    supported = False
    if query.area is not None and isinstance(provider, AreaResearchProvider):
        try:
            supported = provider.supports_area(query) is True
        except Exception:
            supported = False
    explanation = provider_capabilities(provider).spatial_scope
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
    if len(providers) > MAX_COLLECTION_PROVIDERS or len(inventory) != len(providers):
        raise InvalidRequest("Research provider catalogue exceeds its unique source capacity")
    if query.source_ids is not None and not set(query.source_ids).issubset(inventory):
        raise InvalidRequest(
            "Selected sources are unavailable for this research scope. Preview the plan again."
        )
    if any(task.source_id not in inventory for task in query.planned_tasks):
        raise InvalidRequest("Planned task source is unavailable for this research scope")
    tasks = []
    for provider in providers:
        capabilities = provider_capabilities(provider)
        language = capabilities.language
        aliases = tuple(value.lower() for value in capabilities.query_language_aliases)
        variant = task_variant(query, language, aliases)
        routed = replace(query, terms=variant.terms) if variant is not None else query
        provenance = "operator_supplied_variant" if routed is not query else "original_terms"
        temporal_scope = capabilities.temporal_scope
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
                query_variant=variant,
                spatial_supported=spatial_supported,
                spatial_scope=spatial_scope,
                task_id="source:" + provider.id,
                planned_terms_supported=capabilities.supports_planned_terms,
                registry_namespaces=capabilities.registry_namespaces,
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
                query_variant=None,
                spatial_supported=spatial_supported,
                spatial_scope=spatial_scope,
                task_id=task_identity(operator),
                purpose=operator.purpose,
                candidate_id=operator.candidate_id,
                registry_lookup=lookup,
            )
        )
    if len(tasks) + len(supplementary) > MAX_PLAN_TASKS:
        raise InvalidRequest(f"Expanded research plans support at most {MAX_PLAN_TASKS} tasks")
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
        country_isos=query.country_isos,
        research_web_search=query.research_web_search,
        area=query.area,
        time_basis=query.effective_time_basis,
        candidate_hypotheses=query.candidate_hypotheses,
    )

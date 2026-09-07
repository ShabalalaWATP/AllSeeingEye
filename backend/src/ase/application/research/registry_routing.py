"""Resolve explicit operator identifier references without widening provider or query scope."""

from dataclasses import replace

from ase.application.ports.research import ResearchProvider
from ase.domain.registry_identifiers import RegistryLookup, registry_subject
from ase.domain.research import ResearchFocus, ResearchQuery
from ase.domain.research_tasks import PlannedQueryTask


def resolve_lookup(query: ResearchQuery, task: PlannedQueryTask) -> RegistryLookup | None:
    if task.route != "candidate_identifier":
        return None
    candidate = next(row for row in query.candidate_hypotheses if row.id == task.candidate_id)
    identifier = next(row for row in candidate.registry_identifiers if row.id == task.identifier_id)
    return RegistryLookup(
        candidate.id,
        identifier.id,
        identifier.namespace,
        identifier.value,
        registry_subject(identifier.namespace, identifier.value),
    )


def supports_lookup(
    provider: ResearchProvider, query: ResearchQuery, lookup: RegistryLookup
) -> bool:
    method = getattr(provider, "registry_subject", None)
    return (
        callable(method)
        and method(lookup.namespace, lookup.original_value) == lookup.subject
        and provider.supports(replace(query, subject=lookup.subject))
    )


def lookup_options(provider: ResearchProvider, query: ResearchQuery) -> tuple[RegistryLookup, ...]:
    if query.focus is not ResearchFocus.COMPANY or query.area is not None:
        return ()
    options = []
    for candidate in query.candidate_hypotheses:
        if candidate.origin != "operator":
            continue
        for identifier in candidate.registry_identifiers:
            value = RegistryLookup(
                candidate.id,
                identifier.id,
                identifier.namespace,
                identifier.value,
                registry_subject(identifier.namespace, identifier.value),
            )
            if supports_lookup(provider, query, value):
                options.append(value)
    return tuple(options)

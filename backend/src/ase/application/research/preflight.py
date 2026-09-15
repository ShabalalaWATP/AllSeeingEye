"""Read-only preview of an exact saved brief, before provider or model admission."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.report_jobs.budget import MAX_CALLS, MAX_OUTPUT_TOKENS
from ase.application.reports.templates import template_for
from ase.application.research.budget import CollectionBudget
from ase.application.source_capabilities import (
    CapabilityReadiness,
    SourceCapabilityRegistry,
)
from ase.application.source_inventory import SourceRequirement
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import (
    BriefLimits,
    BriefValidationError,
    IntelligenceRequirement,
)
from ase.domain.source_capabilities import (
    CAPABILITY_POLICY_VERSION,
    CapabilityRef,
    CapabilityScope,
    DateSupport,
    LanguageSupport,
    SourceBundle,
    SourceCapability,
    UnavailableCapabilityGap,
)


@dataclass(frozen=True, slots=True)
class PreflightScope:
    country_isos: tuple[str, ...]
    focus: ResearchFocus
    subject: str | None
    area_sha256: str | None
    saved_map_resolution_required: bool
    linked_context_checks_required: bool


@dataclass(frozen=True, slots=True)
class PreflightBudget:
    tier: ResearchMode
    required_question_ceiling: int
    tier_source_operations: int
    tier_collection_seconds: int
    source_operation_ceiling: int
    collection_second_ceiling: int
    model_call_ceiling: int
    output_token_ceiling: int
    requested: BriefLimits
    reservations_made: Literal[False] = False


@dataclass(frozen=True, slots=True)
class PreflightSource:
    capability: SourceCapability
    readiness: CapabilityReadiness
    candidate_unverified: bool
    exclusion_reasons: tuple[str, ...]
    date_note: str


@dataclass(frozen=True, slots=True)
class ResearchPreflight:
    brief_id: UUID
    revision: int
    title: str
    as_of: datetime
    scope: PreflightScope
    since: datetime
    until: datetime
    observation_policy: str
    time_basis: EvidenceTimeBasis
    forecast_horizon_days: int | None
    question: str
    requirements: tuple[IntelligenceRequirement, ...]
    budget: PreflightBudget
    source_policy: str
    sources: tuple[PreflightSource, ...]
    unknown_source_ids: tuple[str, ...]
    gaps: tuple[UnavailableCapabilityGap, ...]
    candidate_provider_ids: tuple[str, ...]
    known_origin_group_count: int
    unknown_origin_capability_count: int
    review_reasons: tuple[str, ...]
    preview_only: Literal[True] = True
    admission_checked: Literal[False] = False
    source_relevance_ranked: Literal[False] = False
    provider_calls: Literal[0] = 0
    model_calls: Literal[0] = 0
    model_compatibility: Literal["not_checked"] = "not_checked"
    policy_version: str = CAPABILITY_POLICY_VERSION
    duration_note: str = (
        "Collection allowance plus generation time varies. No measured total-duration estimate "
        "is available. These are ceilings, not a reservation or an expected spend."
    )
    coverage_note: str = (
        "No expenditure occurs during this preview. Candidates pass coarse catalogue checks "
        "only; exact provider support, date coverage, relevance, current permissions and model "
        "capacity must be checked at run admission. No evidence or source connectivity was tested. "
        "Candidate origin counts describe catalogue groups, not corroboration. Stage reservations "
        "and interactive clarification are outside this preview milestone."
    )


def _source_rows(
    brief: ResearchBrief,
    registry: SourceCapabilityRegistry,
    enabled: Mapping[str, bool] | None,
    requirements: Mapping[str, SourceRequirement] | None,
) -> tuple[tuple[PreflightSource, ...], tuple[str, ...]]:
    selected = brief.collection.source_ids
    identifiers = tuple(registry.capabilities) if selected is None else selected
    unknown = tuple(key for key in identifiers if key not in registry.capabilities)
    refs = tuple(CapabilityRef(key) for key in identifiers if key in registry.capabilities)
    if not refs:
        return (), unknown
    selected_registry = SourceCapabilityRegistry(
        tuple(registry.capabilities.values()), (), (SourceBundle("PREFLIGHT", "Preview", refs),)
    )
    resolved = selected_registry.resolve(("PREFLIGHT",), enabled=enabled, requirements=requirements)
    candidate_ids = frozenset(resolved.candidate_provider_ids)
    rows = []
    for row in resolved.capabilities:
        capability = row.capability
        reasons = _exclusions(brief, capability)
        if capability.id not in candidate_ids:
            reasons += (
                "not_a_provider_route" if capability.provider_id is None else row.readiness.value,
            )
        rows.append(
            PreflightSource(
                capability,
                row.readiness,
                not reasons,
                reasons,
                "Current snapshot only; this does not establish evidence in the requested interval."
                if DateSupport.CURRENT_SNAPSHOT in capability.support.dates
                else "Date filtering does not guarantee historical completeness or evidence.",
            )
        )
    return tuple(rows), unknown


def _exclusions(brief: ResearchBrief, capability: SourceCapability) -> tuple[str, ...]:
    scope = brief.scope
    if scope.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
        return ("private_input_scope",)
    if scope.map_view_id is not None or scope.map_origin is not None:
        return ("saved_map_resolution_required",)
    supported = capability.support
    desired = (
        CapabilityScope.AREA
        if scope.effective_area is not None
        else CapabilityScope.COMPANY
        if scope.focus is ResearchFocus.COMPANY
        else CapabilityScope.DOMAIN
        if scope.focus is ResearchFocus.DOMAIN
        else CapabilityScope.TOPIC
    )
    scope_ok = desired in supported.scopes or (
        desired is CapabilityScope.TOPIC
        and bool(scope.country_isos)
        and CapabilityScope.COUNTRY_CONTEXT in supported.scopes
    )
    reasons: tuple[str, ...] = () if scope_ok else ("scope_not_supported",)
    if supported.language_policy is not LanguageSupport.NOT_FILTERED and not (
        set(supported.languages) & set(brief.collection.languages)
    ):
        reasons += ("language_not_supported",)
    if brief.observation.time_basis is EvidenceTimeBasis.RECORDED and not (
        set(supported.dates) & {DateSupport.RECORDED_INTERVAL, DateSupport.ANNUAL_PERIODS}
    ):
        reasons += ("recorded_interval_not_supported",)
    if (
        scope.effective_area is not None
        and not scope.disclose_area_to_provider
        and capability.route.value == "public_research"
    ):
        reasons += ("area_disclosure_required",)
    return reasons


def _budget(brief: ResearchBrief) -> tuple[PreflightBudget, tuple[str, ...]]:
    tier = CollectionBudget.for_mode(brief.output.depth)
    fields = (
        ("max_external_operations", tier.requests),
        ("max_collection_seconds", int(tier.seconds)),
        ("max_model_calls", MAX_CALLS),
        ("max_output_tokens", MAX_OUTPUT_TOKENS),
    )
    values = [min(getattr(brief.limits, key) or maximum, maximum) for key, maximum in fields]
    conflicts = tuple(
        f"{key}_exceeds_tier_ceiling"
        for key, maximum in fields
        if (getattr(brief.limits, key) or maximum) > maximum
    )
    return PreflightBudget(
        brief.output.depth,
        {ResearchMode.QUICK: 3, ResearchMode.DETAILED: 6, ResearchMode.ADVANCED: 12}[
            brief.output.depth
        ],
        tier.requests,
        int(tier.seconds),
        values[0],
        values[1],
        values[2],
        values[3],
        brief.limits,
    ), conflicts


def preview_brief(
    brief: ResearchBrief,
    access: AccessContext,
    *,
    now: datetime,
    registry: SourceCapabilityRegistry,
    enabled: Mapping[str, bool] | None = None,
    requirements: Mapping[str, SourceRequirement] | None = None,
    bundle_ids: tuple[str, ...] = (),
) -> ResearchPreflight:
    """The caller loads an exact scoped revision and rechecks session/source state on release."""
    access.require_read(brief.identity.owner_id, brief.identity.team_id)
    if now.utcoffset() is None:
        raise ValueError("Preflight requires a timezone-aware clock")
    now = now.astimezone(UTC)
    try:
        template = template_for(brief.output.template_id)
    except ValueError as exc:
        raise BriefValidationError("output.template_id", "Choose a supported template") from exc
    interval = brief.observation.resolved_interval(now)
    if interval is None:
        hours = template.strategy.window_hours
        interval = now - timedelta(hours=hours), now
    sources, unknown = _source_rows(brief, registry, enabled, requirements)
    budget, review = _budget(brief)
    scope = brief.scope
    saved_map = scope.map_view_id is not None or scope.map_origin is not None
    linked = (
        saved_map
        or bool(brief.private_inputs)
        or any(
            value is not None
            for value in (scope.plan_id, scope.parent_report_id, scope.origin_report_id)
        )
    )
    if linked:
        review += ("linked_context_authorisation_not_checked",)
    if saved_map:
        review += ("saved_map_resolution_required",)
    if unknown:
        review += ("unknown_source_ids",)
    if brief.collection.web_search:
        review += ("fresh_web_model_and_separate_allowance_not_checked",)
    if any(row.expires_at is not None and row.expires_at <= now for row in brief.private_inputs):
        review += ("private_input_expired",)
    candidates = tuple(row.capability.id for row in sources if row.candidate_unverified)
    if not candidates and scope.focus not in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
        review += ("no_catalogue_candidates",)
    selected = brief.question.requirements or (
        IntelligenceRequirement("main", brief.question.main),
    )
    groups = {row.capability.origin_group for row in sources if row.candidate_unverified}
    return ResearchPreflight(
        brief.identity.id,
        brief.identity.revision,
        brief.identity.title,
        now,
        PreflightScope(
            scope.country_isos,
            scope.focus,
            scope.subject,
            None if saved_map else scope.area_hash,
            saved_map,
            linked,
        ),
        *interval,
        brief.observation.policy,
        brief.observation.time_basis
        or (
            EvidenceTimeBasis.RESEARCH
            if scope.effective_area or saved_map
            else EvidenceTimeBasis.PUBLICATION
        ),
        brief.observation.forecast_horizon_days,
        brief.question.main,
        selected,
        budget,
        brief.collection.source_policy,
        sources,
        unknown,
        registry.resolve(bundle_ids or _gap_bundles(brief)).gaps,
        candidates,
        len(groups - {None}),
        sum(row.candidate_unverified and row.capability.origin_group is None for row in sources),
        review,
    )


def _gap_bundles(brief: ResearchBrief) -> tuple[str, ...]:
    scope = brief.scope
    if scope.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
        return ()
    if scope.effective_area is not None or scope.map_view_id is not None:
        return ("AREA",)
    if scope.focus in (ResearchFocus.COMPANY, ResearchFocus.DOMAIN):
        return ("TRADE",) if scope.focus is ResearchFocus.COMPANY else ("CTI",)
    mapped = {
        "cyber": ("CTI", "NETWORK"),
        "economic": ("MACRO", "TRADE"),
        "disaster": ("HAZARD",),
        "humanitarian": ("HUMANITARIAN",),
        "conflict": ("CONFLICT",),
        "news": ("NEWS",),
    }
    return tuple(
        dict.fromkeys(
            key for category in scope.categories for key in mapped.get(category.value, ())
        )
    ) or ("NEWS", "OFFICIAL")

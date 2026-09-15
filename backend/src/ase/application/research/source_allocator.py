"""Pure E01 source planning. Current admission and reviewed profiles are caller inputs.

One operation is reserved per selected provider. No network, models, clocks, query
rewrites or resumable-ledger mutations occur here. Recheck admission before dispatch;
the collector must enforce the returned phase caps and host concurrency separately.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ase.application.research.source_allocation_types import (
    DEPTH_CAPS,
    RESERVATION_QUOTAS,
    WEIGHTS,
    AllocationProfile,
    PhaseAllocation,
    ReservationReceipt,
    SourceAllocation,
    SourceAllocationReceipt,
)
from ase.application.source_capabilities import CapabilityReadiness, ResolvedCapability
from ase.domain.research import ResearchFocus, ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS
from ase.domain.source_capabilities import CapabilityScope, ContentCapability, DateSupport

_READY = {CapabilityReadiness.PUBLIC_UNVERIFIED, CapabilityReadiness.CONFIGURED_UNVERIFIED}
_STOP = frozenset(
    [
        "the",
        "and",
        "what",
        "which",
        "this",
        "that",
        "from",
        "with",
        "during",
        "evidence",
        "source",
        "changes",
        "changed",
        "assess",
        "reported",
        "selected",
        "period",
        "implications",
        "development",
        "developments",
    ]
)


@dataclass(frozen=True, slots=True)
class _Ranked:
    row: ResolvedCapability
    receipt: SourceAllocationReceipt
    primary: bool
    local: bool

    @property
    def score(self) -> int:
        return sum(value for _, value in self.receipt.score_components)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        word
        for word in re.findall(r"[^\W_]+", text.casefold())
        if len(word) >= 3 and word not in _STOP
    )


def _scope(query: ResearchQuery) -> CapabilityScope:
    if query.area is not None:
        return CapabilityScope.AREA
    if query.focus is ResearchFocus.COMPANY:
        return CapabilityScope.COMPANY
    if query.focus is ResearchFocus.DOMAIN:
        return CapabilityScope.DOMAIN
    return CapabilityScope.COUNTRY_CONTEXT if query.country_isos else CapabilityScope.TOPIC


def _rank(
    query: ResearchQuery,
    requirements: tuple[IntelligenceRequirement, ...],
    row: ResolvedCapability,
    profile: AllocationProfile,
) -> _Ranked:
    capability = row.capability
    terms = _tokens(" ".join(profile.terms))
    matched = tuple(req for req in requirements if _tokens(req.question) & terms)
    subject = len(_tokens(query.subject or "") & terms)
    question = len(_tokens(query.question) & terms)
    operator_terms = len(_tokens(" ".join(query.terms)) & terms)
    # A drawn area is itself the subject for sources that only search by area, and an
    # operator's explicit source choice is a reviewed decision, not a keyword guess.
    area_bound = query.area is not None and capability.support.scopes == (CapabilityScope.AREA,)
    explicit = query.source_ids is not None and capability.id in query.source_ids
    relevant = bool(matched or subject or question or operator_terms or area_bound or explicit)
    primary = (
        relevant
        and profile.primary_content
        and capability.content
        in {
            ContentCapability.STRUCTURED,
            ContentCapability.PRIVATE_PASSAGES,
        }
    )
    native = set(capability.support.languages) & (set(query.languages) - {"en"})
    local = (
        relevant
        and profile.local_language
        and bool(native)
        and capability.family != "news_discovery"
    )
    components = (
        (
            "requirements",
            sum(
                (13 - req.priority)
                * WEIGHTS["required" if req.required else "optional"]
                * min(len(_tokens(req.question) & terms), 3)
                for req in matched
            ),
        ),
        ("subject", min(subject, 3) * WEIGHTS["subject"]),
        ("question", min(question, 4) * WEIGHTS["question"]),
        ("operator_terms", min(operator_terms, 4) * WEIGHTS["operator_terms"]),
        (
            "geography",
            WEIGHTS["geography"] * bool(set(query.country_isos) & set(profile.countries)),
        ),
        (
            "language",
            WEIGHTS["language"] * bool(set(query.languages) & set(capability.support.languages)),
        ),
        ("primary", WEIGHTS["primary"] * primary),
    )
    receipt = SourceAllocationReceipt(
        capability.id,
        "eligible" if relevant else "excluded",
        () if relevant else ("no_reviewed_relevance",),
        tuple(req.id for req in matched),
        components,
        capability.support.languages,
        capability.support.dates,
    )
    return _Ranked(row, receipt, primary, local)


def _choose(
    pool: list[_Ranked],
    chosen: list[_Ranked],
    limit: int,
    count: int,
) -> None:
    for _ in range(min(count, limit - len(chosen))):
        remaining = [row for row in pool if row not in chosen]
        if not remaining:
            return
        origins = {row.row.capability.origin_group for row in chosen}
        chosen.append(
            min(
                remaining,
                key=lambda row: (
                    -(
                        row.score
                        - WEIGHTS["same_origin_penalty"]
                        * (row.row.capability.origin_group in origins)
                    ),
                    row.row.capability.id,
                ),
            )
        )


def _cover_requirements(
    requirements: tuple[IntelligenceRequirement, ...],
    pool: list[_Ranked],
    chosen: list[_Ranked],
    limit: int,
) -> None:
    for requirement in requirements:
        if not any(requirement.id in row.receipt.requirement_ids for row in chosen):
            _choose(
                [row for row in pool if requirement.id in row.receipt.requirement_ids],
                chosen,
                limit,
                1,
            )


def _reservations(
    chosen: list[_Ranked], pool: list[_Ranked], quotas: tuple[int, int]
) -> tuple[ReservationReceipt, ...]:
    result = []
    for kind, requested in zip(("primary", "local"), quotas, strict=True):
        available = sum(bool(getattr(row, kind)) for row in pool)
        planned = sum(bool(getattr(row, kind)) for row in chosen)
        reason = (
            "not_requested"
            if not requested
            else "satisfied"
            if planned >= requested
            else "no_relevant_capability"
            if not available
            else "insufficient_relevant_capabilities"
            if available < requested
            else "initial_operation_cap"
        )
        result.append(ReservationReceipt(kind, requested, min(planned, requested), reason))
    return tuple(result)


def allocate_sources(
    query: ResearchQuery,
    requirements: tuple[IntelligenceRequirement, ...],
    resolved: tuple[ResolvedCapability, ...],
    *,
    authorised_ids: frozenset[str],
    provider_support: Mapping[str, bool],
    reviewed_profiles: Mapping[str, AllocationProfile],
    accepted_dates: tuple[DateSupport, ...] = (DateSupport.PUBLICATION_INTERVAL,),
    max_operations: int | None = None,
) -> SourceAllocation:
    """Allocate currently permitted, exactly supported operations with stable ID ties.

    Missing admission, provider support or profile information fails closed. The
    caller derives authorised_ids and support for this exact unchanged query, and
    keeps profiles controlled by reviewed code/data, never generated model scores.
    accepted_dates explicitly permits separate date semantics such as annual data;
    it does not claim a provider has an archive for the requested interval.
    """
    ids = {row.capability.id for row in resolved}
    if (
        not isinstance(requirements, tuple)
        or len(requirements) > 12
        or any(not isinstance(row, IntelligenceRequirement) for row in requirements)
        or len({row.id for row in requirements}) != len(requirements)
        or len(resolved) > MAX_COLLECTION_PROVIDERS
        or len(ids) != len(resolved)
        or not isinstance(authorised_ids, frozenset)
        or not set(reviewed_profiles) <= ids
        or not set(provider_support) <= ids
        or any(not isinstance(row, AllocationProfile) for row in reviewed_profiles.values())
        or not isinstance(accepted_dates, tuple)
        or not 1 <= len(accepted_dates) <= 6
        or any(not isinstance(value, DateSupport) for value in accepted_dates)
        or (query.source_ids is not None and not set(query.source_ids) <= ids)
    ):
        raise ValueError("Invalid or unknown source allocation input")
    total, reserved, seconds, challenge_seconds, items, challenge_items = DEPTH_CAPS[query.mode]
    maximum = total if max_operations is None else max_operations
    if type(maximum) is not int or not 0 <= maximum <= total:
        raise ValueError("Operation limit exceeds the selected depth policy")
    reserved = min(reserved, maximum)
    limit = maximum - reserved
    phases = PhaseAllocation(limit, reserved, seconds, challenge_seconds, items, challenge_items)
    ordered = tuple(sorted(requirements, key=lambda req: (not req.required, req.priority, req.id)))
    excluded: list[SourceAllocationReceipt] = []
    pool: list[_Ranked] = []
    for row in sorted(resolved, key=lambda row: row.capability.id):
        cap = row.capability
        profile = reviewed_profiles.get(cap.id)
        reasons = tuple(
            reason
            for failed, reason in (
                (query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}, "private_scope"),
                (query.source_ids is not None and cap.id not in query.source_ids, "source_policy"),
                (cap.id not in authorised_ids, "not_authorised"),
                (row.readiness not in _READY, row.readiness.value),
                (cap.provider_id is None, "non_provider_route"),
                (provider_support.get(cap.id) is not True, "exact_provider_support_missing"),
                (_scope(query) not in cap.support.scopes, "unsupported_scope"),
                (
                    bool(cap.support.languages)
                    and not set(query.languages) & set(cap.support.languages),
                    "unsupported_language",
                ),
                (not set(accepted_dates) & set(cap.support.dates), "unsupported_dates"),
                (profile is None, "unreviewed_profile"),
            )
            if failed
        )
        if reasons:
            excluded.append(
                SourceAllocationReceipt(
                    cap.id,
                    "excluded",
                    reasons,
                    declared_languages=cap.support.languages,
                    declared_dates=cap.support.dates,
                )
            )
        elif profile is not None:
            ranked = _rank(query, ordered, row, profile)
            if ranked.receipt.disposition == "excluded":
                excluded.append(ranked.receipt)
            else:
                pool.append(ranked)
    quotas = RESERVATION_QUOTAS[query.mode]
    if not (set(query.languages) - {"en"}):
        quotas = (quotas[0], 0)
    reserved_initial = sum(
        min(target, sum(bool(getattr(row, kind)) for row in pool))
        for kind, target in zip(("primary", "local"), quotas, strict=True)
    )
    chosen: list[_Ranked] = []
    required = tuple(req for req in ordered if req.required)
    # Primary/local operations can satisfy requirements too. Leave their slots free
    # initially, then revisit uncovered requirements when reservations overlap.
    _cover_requirements(required, pool, chosen, max(0, limit - reserved_initial))
    for kind, target in zip(("primary", "local"), quotas, strict=True):
        _choose(
            [row for row in pool if getattr(row, kind)],
            chosen,
            limit,
            max(0, target - sum(bool(getattr(row, kind)) for row in chosen)),
        )
    _cover_requirements(required, pool, chosen, limit)
    _choose(pool, chosen, limit, limit)
    receipts = excluded + [
        SourceAllocationReceipt(
            row.receipt.source_id,
            "planned" if row in chosen else "not_planned_capacity",
            () if row in chosen else ("initial_operation_cap",),
            row.receipt.requirement_ids,
            row.receipt.score_components,
            row.receipt.declared_languages,
            row.receipt.declared_dates,
        )
        for row in pool
    ]
    return SourceAllocation(
        tuple(row.row.capability.id for row in chosen),
        tuple(sorted(receipts, key=lambda row: row.source_id)),
        _reservations(chosen, pool, quotas),
        tuple(
            (
                req.id,
                tuple(
                    row.row.capability.id for row in chosen if req.id in row.receipt.requirement_ids
                ),
            )
            for req in ordered
        ),
        phases,
        len(resolved),
        len(pool),
        len({row.row.capability.origin_group for row in chosen} - {None}),
        sum(row.row.capability.origin_group is None for row in chosen),
    )

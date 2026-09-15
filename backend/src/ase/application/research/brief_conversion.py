"""Conservative legacy request bridge while Research Brief admission is introduced."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from ase.application.reports.request import ReportRequest
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_scope import (
    BriefCollection,
    BriefObservation,
    BriefPrivateInput,
    BriefScope,
)
from ase.domain.research_brief_values import (
    BriefIdentity,
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
    BriefValidationError,
    LensId,
)


def brief_from_legacy_request(
    request: ReportRequest,
    *,
    brief_id: UUID,
    owner_id: UUID,
    title: str,
    created_at: datetime,
) -> ResearchBrief:
    """Carry existing request choices, leaving missing new preferences explicitly unset."""
    if not isinstance(request, ReportRequest):
        raise BriefValidationError("request", "Use a validated report request")
    if request.research_mode is None or request.question is None:
        raise BriefValidationError("question.main", "Only question-led research can become a brief")
    if request.parent_report_id is not None and request.parent_version is None:
        raise BriefValidationError("scope.parent_version", "Resolve the exact parent version first")
    if request.research_since is not None:
        observation = BriefObservation(
            "explicit",
            since=request.research_since,
            until=request.research_until,
            time_basis=request.research_time_basis,
        )
    elif request.window_hours is not None:
        observation = BriefObservation(
            "relative",
            lookback_hours=request.window_hours,
            time_basis=request.research_time_basis,
        )
    else:
        observation = BriefObservation("template_default", time_basis=request.research_time_basis)
    scope = BriefScope(
        country_isos=request.country_isos,
        focus=request.research_focus,
        subject=request.research_subject,
        conflict_id=request.conflict_id,
        hazard=request.hazard,
        categories=request.categories,
        area=request.research_area,
        map_origin=request.map_origin,
        map_view_id=request.map_view_id if request.map_origin is None else None,
        map_revision_id=request.map_revision_id if request.map_origin is None else None,
        disclose_area_to_provider=request.disclose_area_to_provider,
        plan_id=request.plan_id,
        parent_report_id=request.parent_report_id,
        parent_version=request.parent_version,
    )
    return ResearchBrief(
        identity=BriefIdentity(
            brief_id,
            1,
            owner_id,
            title,
            created_at,
            created_at,
            team_id=request.team_id,
            origin="legacy-derived",
        ),
        question=BriefQuestion(request.question),
        scope=scope,
        observation=observation,
        lens=BriefLens(LensId.GENERAL, challenge_conclusions=request.devils_advocacy),
        collection=BriefCollection(
            languages=request.research_languages,
            terms=request.research_terms,
            query_variants=request.research_query_variants,
            source_policy="selected_only"
            if request.research_source_ids is not None
            else "all_eligible",
            source_ids=request.research_source_ids,
            web_search=request.research_web_search,
            candidate_hypotheses=request.research_candidate_hypotheses,
            planned_tasks=request.research_planned_tasks,
        ),
        output=BriefOutput(
            depth=request.research_mode,
            language=request.report_language,
            style=request.report_style,
            template_id=request.template_id,
            model_profile_id=request.profile_id,
        ),
        limits=BriefLimits(policy_id="legacy-inherited-v1"),
        monitoring=BriefMonitoring(),
        private_inputs=(BriefPrivateInput("session", input_id=request.research_input_id),)
        if request.research_input_id is not None
        else (),
    )


def _unsupported_field(brief: ResearchBrief) -> str | None:
    """Name the first authored setting the report engine cannot honour yet."""
    checks = (
        ("question.requirements", bool(brief.question.requirements)),
        ("question.exclusions", bool(brief.question.exclusions)),
        ("scope.reviewed_aliases", bool(brief.scope.reviewed_aliases)),
        ("observation.forecast_horizon_days", brief.observation.forecast_horizon_days is not None),
        ("lens.id", brief.lens.id is not LensId.GENERAL),
        ("lens.audience", brief.lens.audience is not None),
        ("lens.decision_need", brief.lens.decision_need is not None),
        ("lens.relevance_instructions", brief.lens.relevance_instructions is not None),
        ("collection.require_primary", brief.collection.require_primary),
        ("collection.require_local", brief.collection.require_local),
        ("collection.require_opposition", brief.collection.require_opposition),
        ("output.preferred_sections", bool(brief.output.preferred_sections)),
        ("output.chart_preference", brief.output.chart_preference != "auto"),
        ("output.table_preference", brief.output.table_preference != "auto"),
        ("limits.max_passes", brief.limits.max_passes is not None),
        ("limits.max_external_operations", brief.limits.max_external_operations is not None),
        ("limits.max_model_calls", brief.limits.max_model_calls is not None),
        ("limits.max_output_tokens", brief.limits.max_output_tokens is not None),
        ("limits.max_collection_seconds", brief.limits.max_collection_seconds is not None),
        ("monitoring.indicators", bool(brief.monitoring.indicators)),
        ("monitoring.review_conditions", bool(brief.monitoring.review_conditions)),
        ("monitoring.prefer_novelty", brief.monitoring.prefer_novelty is not None),
        (
            "monitoring.organisation_profile_id",
            brief.monitoring.organisation_profile_id is not None,
        ),
        (
            "private_inputs",
            len(brief.private_inputs) > 1
            or any(
                row.kind != "session" or row.disclose_to_provider or row.expires_at is not None
                for row in brief.private_inputs
            ),
        ),
    )
    return next((field for field, unsupported in checks if unsupported), None)


def legacy_request_from_brief(brief: ResearchBrief) -> ReportRequest:
    """Refuse new semantics that the old request cannot carry without loss."""
    unsupported = _unsupported_field(brief)
    if unsupported is not None:
        raise BriefValidationError(
            unsupported, "This choice needs canonical admission to be honoured"
        )
    return ReportRequest(
        template_id=brief.output.template_id,
        country_isos=brief.scope.country_isos,
        categories=brief.scope.categories,
        question=brief.question.main,
        window_hours=brief.observation.lookback_hours,
        profile_id=brief.output.model_profile_id,
        devils_advocacy=brief.lens.challenge_conclusions,
        hazard=brief.scope.hazard,
        conflict_id=brief.scope.conflict_id,
        plan_id=brief.scope.plan_id,
        team_id=brief.identity.team_id,
        research_mode=brief.output.depth,
        research_languages=brief.collection.languages,
        research_source_ids=brief.collection.source_ids,
        research_terms=brief.collection.terms,
        research_query_variants=brief.collection.query_variants,
        research_candidate_hypotheses=brief.collection.candidate_hypotheses,
        research_planned_tasks=brief.collection.planned_tasks,
        research_focus=brief.scope.focus,
        research_subject=brief.scope.subject,
        research_input_id=brief.private_inputs[0].input_id if brief.private_inputs else None,
        parent_report_id=brief.scope.parent_report_id,
        parent_version=brief.scope.parent_version,
        report_language=brief.output.language,
        report_style=brief.output.style,
        map_view_id=brief.scope.map_origin.view_id
        if brief.scope.map_origin is not None
        else brief.scope.map_view_id,
        map_revision_id=brief.scope.map_origin.revision_id
        if brief.scope.map_origin is not None
        else brief.scope.map_revision_id,
        disclose_area_to_provider=brief.scope.disclose_area_to_provider,
        map_origin=brief.scope.map_origin,
        research_since=brief.observation.since,
        research_until=brief.observation.until,
        research_time_basis=brief.observation.time_basis,
        research_area=brief.scope.area,
        research_web_search=brief.collection.web_search,
    )


def run_request_from_brief(brief: ResearchBrief, *, now: datetime) -> ReportRequest:
    """Admit supported brief choices without losing authored intelligence requirements."""
    brief.require_live_inputs(now=now)
    legacy_shape = replace(brief, question=replace(brief.question, requirements=()))
    request = legacy_request_from_brief(legacy_shape)
    interval = brief.observation.resolved_interval(now)
    if brief.observation.policy == "relative" and interval is not None:
        request = replace(
            request,
            window_hours=None,
            research_since=interval[0],
            research_until=interval[1],
        )
    return replace(request, canonical_requirements=brief.question.requirements)

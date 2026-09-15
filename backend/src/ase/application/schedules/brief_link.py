"""Exact Research Brief loading and standing subscription request conversion."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import TEMPLATES
from ase.application.research.brief_conversion import run_request_from_brief
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import BriefValidationError


def standing_request_from_brief(brief: ResearchBrief, *, now: datetime) -> ReportRequest:
    """Keep authored settings, resolving the rolling clock only at each due slot."""
    brief.require_subscription_ready(now=now)
    brief.require_live_inputs(now=now)
    if brief.observation.policy == "explicit":
        raise BriefValidationError(
            "observation.policy", "A subscription needs a relative or template-default window"
        )
    request = run_request_from_brief(brief, now=now)
    template = TEMPLATES.get(request.template_id)
    if template is None:
        raise BriefValidationError("output.template_id", "Choose a supported report template")
    hours = brief.observation.lookback_hours or template.strategy.window_hours
    return replace(
        request,
        window_hours=hours,
        research_since=None,
        research_until=None,
        automation=True,
    )

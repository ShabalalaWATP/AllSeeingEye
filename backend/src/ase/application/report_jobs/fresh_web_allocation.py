"""Frozen opt-in discovery allowance within the existing report model-call ledger."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ase.application.report_jobs.stage_reservations import ModelStage
from ase.domain.web_research import (
    WEB_ALLOCATED_OUTPUT_TOKENS,
    WEB_ALLOCATED_REQUESTS,
    WEB_ALLOCATED_SECONDS,
    WEB_ALLOCATED_TOOL_CALLS,
    WEB_ALLOCATION_POLICY,
    WEB_SOURCE_ID,
)

WEB_PLAN_KEY = "fresh_web_discovery_plan"


def web_discovery_plan() -> dict[str, Any]:
    """One optional generated-context request, separate from source-phase limits."""
    return {
        "policy_version": WEB_ALLOCATION_POLICY,
        "source_id": WEB_SOURCE_ID,
        "evidence_role": "generated_context",
        "request_limit": WEB_ALLOCATED_REQUESTS,
        "tool_call_limit": WEB_ALLOCATED_TOOL_CALLS,
        "deadline_seconds": WEB_ALLOCATED_SECONDS,
        "output_token_limit": WEB_ALLOCATED_OUTPUT_TOKENS,
    }


def validate_web_discovery_plan(value: object) -> dict[str, Any]:
    expected = web_discovery_plan()
    if (
        type(value) is not dict
        or set(value) != set(expected)
        or any(type(value[key]) is not type(expected[key]) for key in expected)
        or value != expected
    ):
        raise ValueError("The frozen fresh-web discovery plan is invalid")
    return expected


def freeze_web_discovery(payload: dict[str, Any]) -> None:
    """Attach only to an unpaid candidate before its admission transaction."""
    if WEB_PLAN_KEY in payload or type(payload.get("calls")) is not list or payload["calls"]:
        raise ValueError("Fresh-web allocation requires a new unpaid report job")
    payload[WEB_PLAN_KEY] = web_discovery_plan()


def check_web_discovery_dispatch(
    payload: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    *,
    schema: str,
    stage: ModelStage | None,
    reserved_output: int,
) -> bool:
    """One failed, uncertain or completed web call consumes the frozen dispatch."""
    if WEB_PLAN_KEY not in payload:
        return True  # A previously admitted legacy job retains its lifetime rules.
    plan = validate_web_discovery_plan(payload[WEB_PLAN_KEY])
    web_schema = schema == "web_search"
    web_stage = stage is ModelStage.FRESH_WEB
    if web_schema != web_stage:
        raise ValueError("A fresh-web model call needs its exact frozen stage")
    if not web_schema:
        return True
    return (
        type(reserved_output) is int
        and 1 <= reserved_output <= plan["output_token_limit"]
        and sum(call.get("schema") == "web_search" for call in calls) < plan["request_limit"]
    )

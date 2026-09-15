"""Opt-in stage-budget checkpoint seam, without production pipeline activation.

Admission may freeze a plan only before any paid call. An opted-in worker must
also require the plan so missing metadata cannot silently select legacy rules.
Legacy jobs without either marker retain their existing lifetime accounting.
"""

import json
from collections.abc import Mapping, Sequence
from typing import Any

from ase.application.report_jobs.stage_reservations import (
    POLICY_VERSION,
    DispatchDecision,
    ModelStage,
    StagePlan,
    check_stage_dispatch,
    stage_plan_from_dict,
)

POLICY_KEY = "model_stage_policy"
PLAN_KEY = "model_stage_plan"


def freeze_stage_budget(payload: dict[str, Any], plan: StagePlan) -> None:
    """Add immutable opt-in metadata to an unpaid admission candidate, once.

    This changes only the supplied candidate. The host must persist it with the
    job admission transaction. It must not retrofit paid or resumed legacy jobs.
    """
    if (
        POLICY_KEY in payload
        or PLAN_KEY in payload
        or type(payload.get("calls")) is not list
        or payload["calls"]
    ):
        raise ValueError("Stage planning requires a new, unpaid job without an existing plan.")
    validated = stage_plan_from_dict(plan.to_dict())
    frozen = json.loads(json.dumps(validated.to_dict()))
    payload.update({POLICY_KEY: POLICY_VERSION, PLAN_KEY: frozen})


def check_stage_budget(
    payload: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    stage: ModelStage | None,
    reserved_output: int,
    *,
    required: bool,
) -> DispatchDecision | None:
    """Return legacy None or an opt-in decision inside the atomic ledger mutation.

    Invalid/missing opted-in metadata raises before dispatch. The host must
    preserve both markers on resume and require the plan for opted-in workers.
    Caller-supplied calls must be the complete lifetime ledger in this mutation.
    """
    if not required and POLICY_KEY not in payload and PLAN_KEY not in payload:
        return None
    saved = payload.get(PLAN_KEY)
    if payload.get(POLICY_KEY) != POLICY_VERSION or type(saved) is not dict:
        raise ValueError("The required versioned model-stage plan is unavailable.")
    plan = stage_plan_from_dict(saved)
    if not isinstance(stage, ModelStage):
        return DispatchDecision(
            False, ("Every opted-in provider call requires an explicit stage.",)
        )
    return check_stage_dispatch(plan, calls, stage, reserved_output)

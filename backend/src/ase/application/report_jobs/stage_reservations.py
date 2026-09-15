"""Pure R04 capacity policy; this does not reserve or dispatch provider work.

Freeze the plan for newly admitted jobs. Legacy jobs without this policy retain
their existing lifetime ledger rules; never retrofit a plan onto paid history.
Inside the durable ledger's lease-fenced reservation
mutation, check the complete lifetime ledger before appending a stage-tagged call.
Retries, splits and model-backed web calls need their own entries. A successful
decision is advisory until that check and append share the existing transaction.
"""

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from ase.application.report_jobs.budget_limits import MAX_CALLS, MAX_OUTPUT_TOKENS, token_count

POLICY_VERSION = "ase-stage-reservations-v1"


class ModelStage(StrEnum):
    DIRECTION = "direction"
    SUPPLEMENTARY_PLANNING = "supplementary_planning"
    QUERY_TRANSLATION = "query_translation"
    LEGACY_CONTINUATION = "legacy_continuation"
    TOPIC_DRAFTING = "topic_drafting"
    INITIAL_SYNTHESIS = "initial_synthesis"
    CHALLENGE_PLANNING = "challenge_planning"
    CHALLENGE_REVIEW = "challenge_review"
    TOPIC_REDRAFTS = "topic_redrafts"
    UPDATED_SYNTHESIS = "updated_synthesis"
    FINAL_ADJUDICATION = "final_adjudication"
    REPAIR = "repair"
    SPECIALIST = "specialist"
    FRESH_WEB = "fresh_web"


STAGE_MAX_CALLS = dict(zip(ModelStage, (1, 1, 1, 1, 8, 2, 1, 1, 2, 2, 1, 1, 1, 1), strict=True))
OMISSION_ORDER = (
    ModelStage.SPECIALIST,
    ModelStage.FRESH_WEB,
    ModelStage.LEGACY_CONTINUATION,
    ModelStage.SUPPLEMENTARY_PLANNING,
    ModelStage.QUERY_TRANSLATION,
    ModelStage.TOPIC_DRAFTING,
)


@dataclass(frozen=True, slots=True)
class StageDemand:
    stage: ModelStage
    calls: int
    output_tokens_per_call: int
    # None protects all nonoptional calls and all initial topics. A lower topic
    # minimum explicitly identifies dispensable splits; translation minimum 1
    # makes translation essential. No other required stage can be weakened.
    minimum_calls: int | None = None


@dataclass(frozen=True, slots=True)
class StageAllocation:
    stage: ModelStage
    requested_calls: int
    calls: int
    minimum_calls: int
    output_tokens_per_call: int


@dataclass(frozen=True, slots=True)
class StageOmission:
    stage: ModelStage
    calls: int
    reason: str = "Insufficient model-call or output/reasoning-token capacity."


@dataclass(frozen=True, slots=True)
class StagePlan:
    admitted: bool
    allocations: tuple[StageAllocation, ...]
    omissions: tuple[StageOmission, ...]
    reasons: tuple[str, ...]
    call_limit: int
    output_token_limit: int
    mandatory_calls: int
    mandatory_output_tokens: int
    policy_version: str = POLICY_VERSION

    @property
    def reserved_calls(self) -> int:
        return sum(row.calls for row in self.allocations)

    @property
    def reserved_output_tokens(self) -> int:
        return sum(row.calls * row.output_tokens_per_call for row in self.allocations)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe values, without model identifiers, credentials or provider text."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()
    used_calls: int = 0
    used_output_tokens: int = 0
    remaining_mandatory_calls: int = 0
    remaining_mandatory_output_tokens: int = 0


def _integer(value: object, lower: int, upper: int) -> bool:
    return type(value) is int and lower <= value <= upper


def _allocation(demand: StageDemand) -> StageAllocation:
    if not isinstance(demand.stage, ModelStage) or not _integer(
        demand.calls, 1, STAGE_MAX_CALLS[demand.stage]
    ):
        raise ValueError("Each known model stage requires a bounded dispatch count.")
    if not _integer(demand.output_tokens_per_call, 1, MAX_OUTPUT_TOKENS):
        raise ValueError("A frozen per-call output/reasoning maximum is required.")
    optional = demand.stage in OMISSION_ORDER and demand.stage is not ModelStage.TOPIC_DRAFTING
    minimum = demand.minimum_calls
    if minimum is None:
        minimum = 0 if optional else demand.calls
    if not _integer(minimum, 0, demand.calls):
        raise ValueError("Required dispatches must fit the requested stage allocation.")
    if demand.stage is ModelStage.TOPIC_DRAFTING and minimum == 0:
        raise ValueError("Initial topics cannot all be silently omitted.")
    if not optional and demand.stage is not ModelStage.TOPIC_DRAFTING and minimum != demand.calls:
        raise ValueError("Only optional work and explicitly extra topic splits may be omitted.")
    return StageAllocation(
        demand.stage, demand.calls, demand.calls, minimum, demand.output_tokens_per_call
    )


def build_stage_plan(
    demands: Sequence[StageDemand],
    *,
    call_limit: int = MAX_CALLS,
    output_token_limit: int = MAX_OUTPUT_TOKENS,
) -> StagePlan:
    """Plan a new lifetime allowance; never call this to reset a resumed job.

    Every requested nonoptional dispatch is protected, including requested synthesis
    retries and affected redrafts. If these cannot fit, the caller must refuse new
    work or retain an affected judgement as needs-review, not reuse its conclusion.
    """
    if not _integer(call_limit, 1, MAX_CALLS) or not _integer(
        output_token_limit, 1, MAX_OUTPUT_TOKENS
    ):
        raise ValueError("Requested limits must be within the existing job ceilings.")
    if len(demands) > len(ModelStage):
        raise ValueError("Too many stage requests.")
    allocations = tuple(_allocation(demand) for demand in demands)
    rows = {row.stage: row for row in allocations}
    if len(rows) != len(demands):
        raise ValueError("Stage requests must be unique.")
    mandatory = sum(row.minimum_calls for row in rows.values())
    mandatory_tokens = sum(row.minimum_calls * row.output_tokens_per_call for row in rows.values())
    missing = {ModelStage.INITIAL_SYNTHESIS, ModelStage.FINAL_ADJUDICATION} - rows.keys()
    reasons: tuple[str, ...] = (
        ("Initial synthesis and final adjudication must both be reserved.",) if missing else ()
    )
    if mandatory > call_limit or mandatory_tokens > output_token_limit:
        reasons += ("Mandatory stages cannot fit the frozen model maxima and job limits.",)
    if reasons:
        return StagePlan(
            False, (), (), reasons, call_limit, output_token_limit, mandatory, mandatory_tokens
        )
    counts = {stage: row.calls for stage, row in rows.items()}
    omissions = []
    for stage in OMISSION_ORDER:
        row = rows.get(stage)
        if row is None:
            continue
        while counts[stage] > row.minimum_calls and (
            sum(counts.values()) > call_limit
            or sum(counts[key] * value.output_tokens_per_call for key, value in rows.items())
            > output_token_limit
        ):
            counts[stage] -= 1
        if counts[stage] < row.calls:
            omissions.append(StageOmission(stage, row.calls - counts[stage]))
    allocations = tuple(
        StageAllocation(
            stage, row.requested_calls, counts[stage], row.minimum_calls, row.output_tokens_per_call
        )
        for stage in ModelStage
        if (row := rows.get(stage)) is not None
    )
    return StagePlan(
        True,
        allocations,
        tuple(omissions),
        (),
        call_limit,
        output_token_limit,
        mandatory,
        mandatory_tokens,
    )


def stage_plan_from_dict(value: Mapping[str, Any]) -> StagePlan:
    """Validate a saved admitted plan by reproducing its exact versioned decision."""
    try:
        if (
            set(value) != set(StagePlan.__dataclass_fields__)
            or value.get("policy_version") != POLICY_VERSION
            or value.get("admitted") is not True
        ):
            raise ValueError
        allocations = value["allocations"]
        if not isinstance(allocations, list | tuple) or len(allocations) > len(ModelStage):
            raise ValueError
        demands = tuple(
            StageDemand(
                ModelStage(row["stage"]),
                row["requested_calls"],
                row["output_tokens_per_call"],
                row["minimum_calls"],
            )
            for row in allocations
        )
        plan = build_stage_plan(
            demands, call_limit=value["call_limit"], output_token_limit=value["output_token_limit"]
        )
        # JSON round-trips change tuples to lists. Normalise only those containers;
        # do not coerce numbers, policy identifiers or unknown fields.
        if json.dumps(plan.to_dict(), sort_keys=True) != json.dumps(dict(value), sort_keys=True):
            raise ValueError
    except (KeyError, TypeError, ValueError, RecursionError) as error:
        raise ValueError(
            "The saved stage plan is invalid or requires its original policy."
        ) from error
    return plan


def check_stage_dispatch(
    plan: StagePlan,
    calls: Sequence[Mapping[str, Any]],
    stage: ModelStage,
    reserved_output: int,
) -> DispatchDecision:
    """Check an append against complete durable history, without mutating anything.

    Calls use the existing ledger fields plus a required ``stage``. Failed,
    uncertain and in-flight entries consume dispatches. Only completed/failed
    entries with valid known completion usage release unused token reservations.
    """
    try:
        plan = stage_plan_from_dict(plan.to_dict())
    except ValueError:
        return DispatchDecision(False, ("No valid admitted stage plan is available.",))
    rows = {row.stage: row for row in plan.allocations}
    allocation = rows.get(stage) if isinstance(stage, ModelStage) else None
    if (
        allocation is None
        or not _integer(reserved_output, 1, MAX_OUTPUT_TOKENS)
        or (reserved_output != allocation.output_tokens_per_call)
    ):
        return DispatchDecision(False, ("The dispatch does not match a frozen stage allocation.",))
    if len(calls) > plan.call_limit:
        return DispatchDecision(False, ("The lifetime dispatch allowance is exhausted.",))
    counts: Counter[ModelStage] = Counter()
    used, identifiers = 0, set()
    for call in calls:
        try:
            call_stage = ModelStage(call["stage"])
            row = rows[call_stage]
            identifier, status, reserved = call["id"], call["status"], call["reserved_output"]
            if (
                not isinstance(identifier, str)
                or not identifier
                or identifier in identifiers
                or status not in {"in_flight", "completed", "failed", "uncertain"}
                or not _integer(reserved, 1, row.output_tokens_per_call)
                or reserved != row.output_tokens_per_call
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return DispatchDecision(False, ("Lifetime calls need valid, unique stage accounting.",))
        identifiers.add(identifier)
        counts[call_stage] += 1
        known = token_count(call.get("completion_tokens"))
        used += known if known is not None and status in {"completed", "failed"} else reserved
    if counts[stage] >= allocation.calls or any(
        counts[key] > row.calls for key, row in rows.items()
    ):
        return DispatchDecision(False, ("This stage has no remaining admitted dispatches.",))
    after = counts.copy()
    after[stage] += 1
    remaining = {key: max(0, row.minimum_calls - after[key]) for key, row in rows.items()}
    mandatory = sum(remaining.values())
    tokens = sum(remaining[key] * row.output_tokens_per_call for key, row in rows.items())
    fits = len(calls) + 1 + mandatory <= plan.call_limit and (
        used + reserved_output + tokens <= plan.output_token_limit
    )
    return DispatchDecision(
        fits,
        () if fits else ("Lifetime usage and mandatory stage reservations leave no capacity.",),
        len(calls),
        used,
        mandatory,
        tokens,
    )

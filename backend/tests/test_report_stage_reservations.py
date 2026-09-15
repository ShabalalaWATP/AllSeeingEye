"""R04 planning and lifetime checks are pure; durable enforcement is not wired here."""

import json
from copy import deepcopy
from dataclasses import replace
from itertools import permutations

import pytest

from ase.application.report_jobs.budget import MAX_CALLS, MAX_OUTPUT_TOKENS
from ase.application.report_jobs.stage_reservations import (
    OMISSION_ORDER,
    STAGE_MAX_CALLS,
    StageDemand,
    build_stage_plan,
    check_stage_dispatch,
    stage_plan_from_dict,
)
from ase.application.report_jobs.stage_reservations import (
    ModelStage as Stage,
)


def full_work(tokens=10_000):
    return tuple(
        StageDemand(stage, maximum, tokens, 2 if stage is Stage.TOPIC_DRAFTING else None)
        for stage, maximum in STAGE_MAX_CALLS.items()
    )


def minimum_work(tokens=32_000):
    return (
        StageDemand(Stage.INITIAL_SYNTHESIS, 1, tokens),
        StageDemand(Stage.FINAL_ADJUDICATION, 1, tokens),
    )


def call(stage, index, tokens=32_000, status="uncertain", completion=None):
    return {
        "id": f"call-{index}",
        "stage": stage.value,
        "status": status,
        "reserved_output": tokens,
        "completion_tokens": completion,
    }


def test_maximum_work_reserves_one_shared_24_call_token_allowance():
    plan = build_stage_plan(full_work())
    assert plan.admitted and not plan.omissions
    assert plan.reserved_calls == MAX_CALLS == sum(STAGE_MAX_CALLS.values()) == 24
    assert plan.reserved_output_tokens == 240_000 <= MAX_OUTPUT_TOKENS
    calls = []
    for row in plan.allocations:
        for _ in range(row.calls):
            decision = check_stage_dispatch(plan, calls, row.stage, row.output_tokens_per_call)
            assert decision.allowed
            calls.append(call(row.stage, len(calls), 10_000, "completed", 10_000))
    assert not check_stage_dispatch(plan, calls, Stage.FRESH_WEB, 10_000).allowed


def test_optional_work_is_omitted_in_policy_order_before_extra_topic_splits():
    plan = build_stage_plan(full_work(), call_limit=16)
    assert plan.admitted and plan.reserved_calls == 16
    assert tuple(row.stage for row in plan.omissions) == OMISSION_ORDER
    assert [row.calls for row in plan.omissions] == [1, 1, 1, 1, 1, 3]
    by_stage = {row.stage: row for row in plan.allocations}
    assert by_stage[Stage.TOPIC_DRAFTING].calls == 5
    assert by_stage[Stage.INITIAL_SYNTHESIS].calls == 2
    assert by_stage[Stage.FINAL_ADJUDICATION].calls == 1


def test_token_pressure_preserves_frozen_per_call_maxima_without_downgrade():
    plan = build_stage_plan(full_work(), output_token_limit=160_000)
    assert plan.admitted and plan.reserved_calls == 16
    assert all(row.output_tokens_per_call == 10_000 for row in plan.allocations)
    assert plan.reserved_output_tokens == 160_000
    assert sum(row.calls for row in plan.omissions) == 8


def test_essential_translation_and_required_topics_cannot_be_silently_dropped():
    demands = (
        *minimum_work(100),
        StageDemand(Stage.QUERY_TRANSLATION, 1, 100, 1),
        StageDemand(Stage.TOPIC_DRAFTING, 4, 100, 2),
    )
    admitted = build_stage_plan(demands, call_limit=5)
    assert admitted.admitted
    assert admitted.omissions[0].stage is Stage.TOPIC_DRAFTING
    refused = build_stage_plan(demands, call_limit=4)
    assert not refused.admitted and refused.mandatory_calls == 5
    assert not refused.allocations and refused.reserved_calls == 0
    assert "Mandatory" in refused.reasons[0]


@pytest.mark.parametrize("limits", [{"call_limit": 1}, {"output_token_limit": 63_999}])
def test_mandatory_synthesis_and_adjudication_refuse_insufficient_capacity(limits):
    plan = build_stage_plan(minimum_work(), **limits)
    assert not plan.admitted and plan.mandatory_output_tokens == 64_000
    assert not check_stage_dispatch(plan, [], Stage.INITIAL_SYNTHESIS, 32_000).allowed


def test_large_frozen_profiles_truthfully_refuse_maximum_work_plan():
    plan = build_stage_plan(full_work(32_000))
    assert not plan.admitted and plan.mandatory_output_tokens > MAX_OUTPUT_TOKENS
    assert plan.reserved_output_tokens == 0


@pytest.mark.parametrize("demands", [(), minimum_work()[:1], minimum_work()[1:]])
def test_missing_mandatory_stages_are_not_admitted(demands):
    plan = build_stage_plan(demands)
    assert not plan.admitted and "both be reserved" in plan.reasons[0]


@pytest.mark.parametrize(
    "demand",
    [
        StageDemand("unknown", 1, 100),
        StageDemand(Stage.SPECIALIST, True, 100),
        StageDemand(Stage.SPECIALIST, 2, 100),
        StageDemand(Stage.SPECIALIST, 1, 0),
        StageDemand(Stage.SPECIALIST, 1, True),
        StageDemand(Stage.SPECIALIST, 1, MAX_OUTPUT_TOKENS + 1),
        StageDemand(Stage.SPECIALIST, 1, 100, 2),
        StageDemand(Stage.TOPIC_DRAFTING, 2, 100, 0),
        StageDemand(Stage.FINAL_ADJUDICATION, 1, 100, 0),
    ],
)
def test_invalid_stage_budgets_fail_before_planning(demand):
    with pytest.raises(ValueError):
        build_stage_plan((demand,))


@pytest.mark.parametrize(
    "limits",
    [{"call_limit": 25}, {"call_limit": True}, {"output_token_limit": 256_001}],
)
def test_caller_cannot_increase_system_ceilings(limits):
    with pytest.raises(ValueError):
        build_stage_plan(minimum_work(), **limits)


def test_duplicate_or_overlong_stage_requests_are_rejected():
    with pytest.raises(ValueError):
        build_stage_plan(minimum_work() * 2)
    with pytest.raises(ValueError):
        build_stage_plan(minimum_work() * 8)


def test_plan_is_deterministic_serialisable_and_resume_uses_identical_allocation():
    demands = (*minimum_work(100), StageDemand(Stage.SPECIALIST, 1, 100))
    plan = build_stage_plan(demands, call_limit=2)
    saved = json.loads(json.dumps(plan.to_dict()))
    assert stage_plan_from_dict(saved) == plan
    assert all(build_stage_plan(order, call_limit=2) == plan for order in permutations(demands))
    assert not check_stage_dispatch(plan, [], Stage.SPECIALIST, 100).allowed


@pytest.mark.parametrize("field,value", [("calls", 2), ("calls", True), ("calls", 1.0)])
def test_saved_allocation_cannot_be_tampered_with(field, value):
    saved = json.loads(json.dumps(build_stage_plan(minimum_work()).to_dict()))
    saved["allocations"][0][field] = value
    with pytest.raises(ValueError):
        stage_plan_from_dict(saved)


def test_unknown_policy_or_unexpected_saved_fields_require_explicit_migration():
    saved = build_stage_plan(minimum_work()).to_dict()
    for changed in ({**saved, "policy_version": "future"}, {**saved, "unexpected": 1}):
        with pytest.raises(ValueError):
            stage_plan_from_dict(changed)


@pytest.mark.parametrize("status", ["in_flight", "uncertain", "failed", "completed"])
def test_resume_keeps_unknown_usage_and_spent_dispatches(status):
    plan = build_stage_plan(minimum_work(), output_token_limit=64_000)
    calls = [call(Stage.INITIAL_SYNTHESIS, 1, status=status)]
    before = deepcopy(calls)
    for saved in (plan, stage_plan_from_dict(json.loads(json.dumps(plan.to_dict())))):
        assert not check_stage_dispatch(saved, calls, Stage.INITIAL_SYNTHESIS, 32_000).allowed
        decision = check_stage_dispatch(saved, calls, Stage.FINAL_ADJUDICATION, 32_000)
        assert decision.allowed and decision.used_output_tokens == 32_000
    assert calls == before


def test_actual_usage_overrun_cannot_spend_reserved_mandatory_capacity_on_optional_work():
    demands = (
        *minimum_work(),
        StageDemand(Stage.DIRECTION, 1, 32_000),
        StageDemand(Stage.SPECIALIST, 1, 32_000),
    )
    plan = build_stage_plan(demands, output_token_limit=128_000)
    calls = [call(Stage.DIRECTION, 1, status="completed", completion=40_000)]
    decision = check_stage_dispatch(plan, calls, Stage.SPECIALIST, 32_000)
    assert not decision.allowed and decision.remaining_mandatory_output_tokens == 64_000
    assert check_stage_dispatch(plan, calls, Stage.INITIAL_SYNTHESIS, 32_000).allowed


def test_in_flight_and_uncertain_calls_never_release_reported_partial_usage():
    plan = build_stage_plan(minimum_work())
    for status in ("in_flight", "uncertain"):
        result = check_stage_dispatch(
            plan,
            [call(Stage.INITIAL_SYNTHESIS, 1, status=status, completion=1)],
            Stage.FINAL_ADJUDICATION,
            32_000,
        )
        assert result.allowed and result.used_output_tokens == 32_000


@pytest.mark.parametrize("completion,expected", [(12, 12), (0, 0), (True, 32_000), (-1, 32_000)])
def test_only_valid_settled_usage_releases_unused_tokens(completion, expected):
    result = check_stage_dispatch(
        build_stage_plan(minimum_work()),
        [call(Stage.INITIAL_SYNTHESIS, 1, status="failed", completion=completion)],
        Stage.FINAL_ADJUDICATION,
        32_000,
    )
    assert result.allowed and result.used_output_tokens == expected


def test_retries_redrafts_and_web_wrappers_count_against_their_frozen_stages():
    plan = build_stage_plan(full_work())
    for stage in (
        Stage.TOPIC_DRAFTING,
        Stage.TOPIC_REDRAFTS,
        Stage.INITIAL_SYNTHESIS,
        Stage.FRESH_WEB,
    ):
        calls = [call(stage, index, 10_000, "failed", 0) for index in range(STAGE_MAX_CALLS[stage])]
        assert not check_stage_dispatch(plan, calls, stage, 10_000).allowed


@pytest.mark.parametrize(
    "changes",
    [
        {"stage": "unknown"},
        {"status": "lost"},
        {"reserved_output": True},
        {"reserved_output": 1},
        {"id": ""},
    ],
)
def test_new_stage_policy_refuses_corrupt_or_unclassified_history(changes):
    row = {**call(Stage.INITIAL_SYNTHESIS, 1), **changes}
    assert not check_stage_dispatch(
        build_stage_plan(minimum_work()), [row], Stage.FINAL_ADJUDICATION, 32_000
    ).allowed


def test_untagged_history_is_not_guessed_and_proposed_budget_must_match_snapshot():
    plan = build_stage_plan(minimum_work())
    row = call(Stage.INITIAL_SYNTHESIS, 1)
    row.pop("stage")
    assert not check_stage_dispatch(plan, [row], Stage.FINAL_ADJUDICATION, 32_000).allowed
    for stage, tokens in ((Stage.SPECIALIST, 32_000), (Stage.INITIAL_SYNTHESIS, 100)):
        assert not check_stage_dispatch(plan, [], stage, tokens).allowed
    assert not check_stage_dispatch(
        replace(plan, call_limit=25), [], Stage.INITIAL_SYNTHESIS, 32_000
    ).allowed


def test_duplicate_or_overfull_lifetime_rows_never_restore_capacity():
    plan = build_stage_plan(minimum_work(), call_limit=2)
    row = call(Stage.INITIAL_SYNTHESIS, 1)
    for calls in ([row, row], [row, row, row]):
        assert not check_stage_dispatch(plan, calls, Stage.FINAL_ADJUDICATION, 32_000).allowed


def test_another_stage_overrun_and_unknown_proposed_stage_fail_closed():
    plan = build_stage_plan(minimum_work())
    calls = [call(Stage.INITIAL_SYNTHESIS, index) for index in range(2)]
    assert not check_stage_dispatch(plan, calls, Stage.FINAL_ADJUDICATION, 32_000).allowed
    assert not check_stage_dispatch(plan, [], "initial_synthesis", 32_000).allowed


@pytest.mark.parametrize("allocations", [None, {}, [{}] * 15])
def test_invalid_saved_plan_collections_are_rejected(allocations):
    saved = build_stage_plan(minimum_work()).to_dict()
    with pytest.raises(ValueError):
        stage_plan_from_dict({**saved, "allocations": allocations})


def test_omission_receipts_cannot_change_when_restoring_a_plan():
    plan = build_stage_plan(full_work(), call_limit=16)
    saved = json.loads(json.dumps(plan.to_dict()))
    saved["omissions"][0]["calls"] = 0
    with pytest.raises(ValueError):
        stage_plan_from_dict(saved)

"""Contract tests for the durable, serial source-phase ledger."""

import json
from copy import deepcopy

import pytest

from ase.application.research.phase_ledger import (
    LEDGER_KEY,
    PhaseLedgerError,
    abandon_operation,
    new_phase_ledger,
    reserve_operation,
    settle_operation,
)
from ase.domain.research import ResearchMode


@pytest.mark.parametrize(
    ("mode", "initial", "challenge"),
    [
        (ResearchMode.QUICK, (6, 45_000, 200), (0, 0, 0)),
        (ResearchMode.DETAILED, (20, 135_000, 792), (4, 45_000, 8)),
        (ResearchMode.ADVANCED, (26, 180_000, 988), (6, 60_000, 12)),
    ],
)
def test_depth_limits_are_frozen_and_json_safe(mode, initial, challenge):
    snapshot = json.loads(json.dumps(new_phase_ledger(mode)))
    assert snapshot["version"] == 1
    assert snapshot["mode"] == mode.value
    for name, expected in (("initial", initial), ("challenge", challenge)):
        limits = snapshot["phases"][name]["limits"]
        assert (limits["operations"], limits["active_ms"], limits["items"]) == expected
    assert snapshot["phases"]["initial"]["limits"]["per_request_ms"] == (
        12_000 if mode is ResearchMode.QUICK else 20_000
    )


def test_reservation_is_durable_idempotent_and_serial_within_phase():
    payload = {}
    first = reserve_operation(
        payload, mode=ResearchMode.DETAILED, phase="initial", request_key="task:1"
    )
    assert first.dispatch and first.allowance_ms == 20_000
    assert json.loads(json.dumps(payload))[LEDGER_KEY] == payload[LEDGER_KEY]
    replay = reserve_operation(
        payload, mode=ResearchMode.DETAILED, phase="initial", request_key="task:1"
    )
    assert replay.status == "open" and not replay.dispatch and replay.reason == "replayed"
    blocked = reserve_operation(
        payload, mode=ResearchMode.DETAILED, phase="initial", request_key="task:2"
    )
    assert blocked.reason == "operation_open" and not blocked.dispatch
    assert list(payload[LEDGER_KEY]["phases"]["initial"]["operations"]) == ["task:1"]


def test_known_elapsed_refunds_time_and_settlement_replay_is_exact():
    payload = {}
    reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key="a")
    first = settle_operation(
        payload,
        mode=ResearchMode.QUICK,
        phase="initial",
        request_key="a",
        elapsed_ms=2_000,
        retained_item_keys=("item-1", "item-1", "item-2"),
    )
    assert first.charged_ms == 2_000
    assert first.retained_keys == ("item-1", "item-2")
    assert first.excluded_keys == ()
    assert (
        settle_operation(
            payload,
            mode=ResearchMode.QUICK,
            phase="initial",
            request_key="a",
            elapsed_ms=2_000,
            retained_item_keys=("item-1", "item-1", "item-2"),
        )
        == first
    )
    with pytest.raises(PhaseLedgerError, match="Conflicting"):
        settle_operation(
            payload,
            mode=ResearchMode.QUICK,
            phase="initial",
            request_key="a",
            elapsed_ms=2_001,
            retained_item_keys=("item-1", "item-2"),
        )
    next_operation = reserve_operation(
        payload, mode=ResearchMode.QUICK, phase="initial", request_key="b"
    )
    assert next_operation.dispatch and next_operation.allowance_ms == 12_000


def test_settlement_cannot_charge_more_than_reserved_deadline():
    payload = {}
    reserve_operation(payload, mode=ResearchMode.DETAILED, phase="challenge", request_key="one")
    with pytest.raises(PhaseLedgerError, match="reserved deadline"):
        settle_operation(
            payload,
            mode=ResearchMode.DETAILED,
            phase="challenge",
            request_key="one",
            elapsed_ms=20_001,
            retained_item_keys=(),
        )
    operation = payload[LEDGER_KEY]["phases"]["challenge"]["operations"]["one"]
    assert operation["status"] == "open" and operation["charged_ms"] == 20_000


def test_abandoned_unknown_reservation_is_never_refunded_or_redispatched():
    payload = {}
    reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key="lost")
    assert (
        abandon_operation(
            payload, mode=ResearchMode.QUICK, phase="initial", request_key="lost"
        ).status
        == "unknown"
    )
    assert (
        abandon_operation(
            payload, mode=ResearchMode.QUICK, phase="initial", request_key="lost"
        ).status
        == "unknown"
    )
    replay = reserve_operation(
        payload, mode=ResearchMode.QUICK, phase="initial", request_key="lost"
    )
    assert replay.status == "unknown" and not replay.dispatch
    with pytest.raises(PhaseLedgerError, match="abandoned"):
        settle_operation(
            payload,
            mode=ResearchMode.QUICK,
            phase="initial",
            request_key="lost",
            elapsed_ms=1,
            retained_item_keys=(),
        )
    reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key="next")
    operations = payload[LEDGER_KEY]["phases"]["initial"]["operations"]
    assert operations["lost"]["charged_ms"] == 12_000
    assert operations["next"]["charged_ms"] == 12_000


def test_time_reservation_denies_before_dispatch_without_borrowing_challenge_time():
    payload = {}
    for index in range(7):
        decision = reserve_operation(
            payload, mode=ResearchMode.DETAILED, phase="initial", request_key=f"i:{index}"
        )
        assert decision.dispatch
        abandon_operation(
            payload, mode=ResearchMode.DETAILED, phase="initial", request_key=f"i:{index}"
        )
    assert [
        operation["allowance_ms"]
        for operation in payload[LEDGER_KEY]["phases"]["initial"]["operations"].values()
    ] == [20_000] * 6 + [15_000]
    assert (
        reserve_operation(
            payload, mode=ResearchMode.DETAILED, phase="initial", request_key="too-late"
        ).reason
        == "time_cap"
    )
    challenge = reserve_operation(
        payload, mode=ResearchMode.DETAILED, phase="challenge", request_key="counter"
    )
    assert challenge.dispatch and challenge.allowance_ms == 20_000


def test_initial_item_ceiling_preserves_fresh_challenge_capacity():
    payload = {}
    reserve_operation(payload, mode=ResearchMode.DETAILED, phase="initial", request_key="initial")
    initial = settle_operation(
        payload,
        mode=ResearchMode.DETAILED,
        phase="initial",
        request_key="initial",
        elapsed_ms=100,
        retained_item_keys=tuple(f"item-{index}" for index in range(793)),
    )
    assert len(initial.retained_keys) == 792
    assert initial.excluded_keys == ("item-792",)
    assert (
        reserve_operation(
            payload, mode=ResearchMode.DETAILED, phase="initial", request_key="no-initial-slot"
        ).reason
        == "item_cap"
    )
    reserve_operation(
        payload, mode=ResearchMode.DETAILED, phase="challenge", request_key="challenge"
    )
    challenge = settle_operation(
        payload,
        mode=ResearchMode.DETAILED,
        phase="challenge",
        request_key="challenge",
        elapsed_ms=150,
        retained_item_keys=tuple(f"item-{index}" for index in range(790, 802)),
    )
    assert challenge.retained_keys == tuple(f"item-{index}" for index in range(792, 800))
    assert challenge.excluded_keys == ("item-790", "item-791", "item-800", "item-801")
    assert (
        reserve_operation(
            payload, mode=ResearchMode.DETAILED, phase="challenge", request_key="no-challenge-slot"
        ).reason
        == "item_cap"
    )
    retained = [
        key
        for phase in payload[LEDGER_KEY]["phases"].values()
        for operation in phase["operations"].values()
        for key in operation["retained_keys"]
    ]
    assert len(retained) == len(set(retained)) == 800


def test_basic_has_no_challenge_and_operation_cap_is_enforced():
    payload = {}
    assert (
        reserve_operation(
            payload, mode=ResearchMode.QUICK, phase="challenge", request_key="not-supported"
        ).reason
        == "operation_cap"
    )
    for index in range(6):
        reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key=str(index))
        settle_operation(
            payload,
            mode=ResearchMode.QUICK,
            phase="initial",
            request_key=str(index),
            elapsed_ms=1,
            retained_item_keys=(),
        )
    assert (
        reserve_operation(
            payload, mode=ResearchMode.QUICK, phase="initial", request_key="seventh"
        ).reason
        == "operation_cap"
    )


def test_policy_tampering_and_duplicate_retained_items_fail_closed():
    payload = {}
    reserve_operation(payload, mode=ResearchMode.DETAILED, phase="initial", request_key="one")
    before = deepcopy(payload)
    payload[LEDGER_KEY]["phases"]["initial"]["limits"]["operations"] = 999
    with pytest.raises(PhaseLedgerError, match="policy limits"):
        reserve_operation(payload, mode=ResearchMode.DETAILED, phase="initial", request_key="two")
    assert payload[LEDGER_KEY]["phases"]["initial"]["limits"]["operations"] == 999
    payload = before
    settle_operation(
        payload,
        mode=ResearchMode.DETAILED,
        phase="initial",
        request_key="one",
        elapsed_ms=1,
        retained_item_keys=("same",),
    )
    payload[LEDGER_KEY]["phases"]["initial"]["operations"]["duplicate"] = deepcopy(
        payload[LEDGER_KEY]["phases"]["initial"]["operations"]["one"]
    )
    with pytest.raises(PhaseLedgerError, match="duplicate retained"):
        reserve_operation(payload, mode=ResearchMode.DETAILED, phase="initial", request_key="two")


def test_invalid_inputs_do_not_change_snapshot():
    payload = {}
    with pytest.raises(PhaseLedgerError, match="key"):
        reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key=" bad ")
    assert payload == {}
    reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key="one")
    before = deepcopy(payload)
    with pytest.raises(PhaseLedgerError, match="settlement"):
        settle_operation(
            payload,
            mode=ResearchMode.QUICK,
            phase="initial",
            request_key="one",
            elapsed_ms=True,
            retained_item_keys=(),
        )
    assert payload == before
    with pytest.raises(PhaseLedgerError, match="depth"):
        reserve_operation(payload, mode=ResearchMode.DETAILED, phase="initial", request_key="two")
    assert payload == before


def test_payload_mutations_work_as_checkpoint_callbacks():
    payload = {"stage": "collecting"}
    decisions = []

    def reserve_callback(snapshot):
        decisions.append(
            reserve_operation(
                snapshot, mode=ResearchMode.ADVANCED, phase="initial", request_key="host:task"
            )
        )

    reserve_callback(payload)
    assert decisions[0].dispatch
    restored = json.loads(json.dumps(payload))
    assert restored["stage"] == "collecting"
    assert not reserve_operation(
        restored, mode=ResearchMode.ADVANCED, phase="initial", request_key="host:task"
    ).dispatch

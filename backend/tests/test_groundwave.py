"""Native reference values, budget normalisation and bounded CPU admission."""

import asyncio
from dataclasses import replace
from importlib import import_module
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest

from ase.adapters.routing.groundwave import NtiaGroundwaveSolver
from ase.application.groundwave import GroundwaveStudy
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.groundwave import GroundwaveInput

INPUTS = GroundwaveInput(7, 100, 2, 2, 0.005, 15, max_distance_km=50, sample_count=2)


@pytest.mark.parametrize(
    "args,expected",
    [
        ((0, 0, 0.01, 1000, 301, 1000, 15, 0.005, 0), (184.5, -82.5, -114.9, 1)),
        ((0, 0, 1, 5000, 301, 5000, 15, 0.005, 1), (536.5, -387.5, -459.9, 1)),
        ((5.5, 1.5, 10, 500, 315, 15, 15, 0.005, 0), (151.3, 7.6, -84.8, 0)),
        ((1, 1, 0.45, 1000, 315, 3000, 15, 0.005, 1), (264.3, -129.3, -194.8, 1)),
        ((10, 10, 30, 10000, 315, 5000, 15, 0.005, 0), (1574.9, -1393.3, -1495.3, 1)),
    ],
)
def test_pinned_native_library_matches_ntia_published_examples(args, expected):
    # First five success rows in NTIA/LFMF-test-data LFMF_Examples.csv,
    # commit c593360c1c9f1cde463d98a3bf89447903d95861 (one decimal precision).
    result = import_module("ITS.Propagation.LFMF").LFMF(*args)
    assert result.A_btl__db == pytest.approx(expected[0], abs=0.1)
    assert result.E__dBuVm == pytest.approx(expected[1], abs=0.1)
    assert result.P_rx__dbm == pytest.approx(expected[2], abs=0.1)
    assert result.method == expected[3]


def test_hf_curve_reference_and_user_gain_loss_budget():
    solver = NtiaGroundwaveSolver()
    curve = solver.calculate(INPUTS)
    assert [sample.distance_km for sample in curve] == [1, 50]
    assert curve[0].method == "flat_earth" and curve[1].method == "residue_series"
    assert curve[-1].basic_transmission_loss_db == pytest.approx(136.413424059)
    assert curve[-1].native_reference_field_dbuv_m == pytest.approx(12.474526992)
    assert curve[-1].received_power_dbm == pytest.approx(-86.413424059)
    adjusted = solver.calculate(replace(INPUTS, tx_gain_dbi=3, rx_gain_dbi=2, system_loss_db=1))
    assert adjusted[-1].received_power_dbm == pytest.approx(curve[-1].received_power_dbm + 4)
    assert adjusted[-1].native_reference_field_dbuv_m == curve[-1].native_reference_field_dbuv_m
    stronger = solver.calculate(replace(INPUTS, tx_power_w=1000))
    assert stronger[-1].basic_transmission_loss_db == pytest.approx(
        curve[-1].basic_transmission_loss_db
    )
    assert stronger[-1].received_power_dbm == pytest.approx(curve[-1].received_power_dbm + 10)


@pytest.mark.parametrize(
    "loss,field,method", [(float("nan"), 20, 0), (100, float("inf"), 0), (100, 20, 5)]
)
def test_nonfinite_or_unknown_native_results_are_rejected(monkeypatch, loss, field, method):
    native = Mock(LFMF=Mock(return_value=Mock(A_btl__db=loss, E__dBuVm=field, method=method)))
    monkeypatch.setattr("ase.adapters.routing.groundwave.import_module", lambda _: native)
    with pytest.raises(ValueError, match="invalid result"):
        NtiaGroundwaveSolver().calculate(INPUTS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("frequency_mhz", 30.1),
        ("tx_height_m", 51),
        ("conductivity_sm", 0),
        ("relative_permittivity", float("nan")),
        ("sample_count", 65),
        ("sample_count", True),
        ("max_distance_km", 201),
        ("max_distance_km", 1),
    ],
)
def test_invalid_native_studies_rejected_before_execution(field, value):
    with pytest.raises(ValueError):
        replace(INPUTS, **{field: value})


async def test_rate_limit_and_solver_failure_no_fallback():
    limiter = Mock(hit=Mock(return_value=3))
    solver = Mock(calculate=Mock(side_effect=RuntimeError("internal native path")))
    service = GroundwaveStudy(solver, limiter)
    with pytest.raises(RateLimited):
        await service.calculate(uuid4(), INPUTS)
    solver.calculate.assert_not_called()
    limiter.hit.return_value = None
    with pytest.raises(InvalidRequest, match="No estimated range was substituted") as error:
        await service.calculate(uuid4(), INPUTS)
    assert "internal native path" not in str(error.value)


async def test_timeout_retains_native_slot_until_worker_really_finishes():
    finish, entered = Event(), Event()

    def calculate(_inputs):
        entered.set()
        finish.wait(2)
        return ()

    service = GroundwaveStudy(
        Mock(calculate=calculate), Mock(hit=Mock(return_value=None)), timeout=0.02
    )
    try:
        with pytest.raises(InvalidRequest):
            await service.calculate(uuid4(), INPUTS)
        assert entered.is_set()
        with pytest.raises(RateLimited):
            await service.calculate(uuid4(), INPUTS)
    finally:
        finish.set()
    assert service._task is not None
    await service._task
    assert await service.calculate(uuid4(), INPUTS) == ()


async def test_request_cancellation_does_not_start_another_native_worker():
    finish, entered = Event(), Event()

    def calculate(_inputs):
        entered.set()
        finish.wait(2)
        return ()

    service = GroundwaveStudy(Mock(calculate=calculate), Mock(hit=Mock(return_value=None)))
    request = asyncio.create_task(service.calculate(uuid4(), INPUTS))
    try:
        await asyncio.to_thread(entered.wait, 1)
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        with pytest.raises(RateLimited):
            await service.calculate(uuid4(), INPUTS)
    finally:
        finish.set()
    assert service._task is not None
    await service._task

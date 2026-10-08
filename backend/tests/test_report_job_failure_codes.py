"""Worker failure codes: only frozen-input validation is final, other faults resume."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from ase.application.report_jobs.controls import resume_error_allowed
from ase.application.report_jobs.snapshots import InvalidJobSnapshot, restore_job
from ase.application.report_jobs.views import error_message
from ase.application.research.phase_ledger import PhaseLedgerError
from ase.container.report_job_worker import failure_code


@pytest.mark.parametrize(
    "data",
    [None, {"schema_version": "1"}, {"schema_version": 99}, {"schema_version": 1}],
)
def test_malformed_snapshots_raise_the_dedicated_type(data: Any) -> None:
    with pytest.raises(InvalidJobSnapshot):
        restore_job(data, None, None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "error",
    [InvalidJobSnapshot("Invalid report snapshot version"), PhaseLedgerError("bad ledger")],
)
def test_snapshot_validation_is_not_resumable(error: Exception) -> None:
    assert failure_code(error) == "invalid_snapshot"
    assert not resume_error_allowed(failure_code(error), {})


@pytest.mark.parametrize(
    "error",
    [
        ValueError("Report validation did not complete"),
        ValueError("Report identifiers changed during generation"),
        ValueError(str(uuid4())),
    ],
)
def test_other_value_errors_remain_resumable_with_honest_copy(error: Exception) -> None:
    code = failure_code(error)
    assert code == "generation_incomplete"
    assert resume_error_allowed(code, {})
    message = error_message(code)
    assert message is not None and "provider" not in message and "Start a new" not in message

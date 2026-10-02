"""Nullable SQL result metadata must not turn corrupt rows into valid output."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.adapters.persistence.monthly_report_usage import monthly_usage
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.adapters.persistence.subscription_diagnostics import subscription_diagnostics
from ase.application.report_jobs.budget import JobInterrupted


async def test_active_original_without_bytes_is_rejected_before_releasing_metadata():
    session = AsyncMock()
    session.execute.return_value = Mock(one_or_none=lambda: (object(), None))

    with pytest.raises(ValueError, match="Active original asset has no stored content"):
        await SqlOriginalAssetRepository(session).content(uuid4())


async def test_missing_coalesced_receipt_total_cannot_understate_usage():
    session = AsyncMock()
    session.execute.return_value = Mock(one=lambda: (0, None, 0))

    with pytest.raises(JobInterrupted):
        await monthly_usage(session, uuid4(), None, datetime(2026, 10, 2, tzinfo=UTC))
    assert session.execute.await_count == 1


async def test_missing_filtered_failure_reason_is_rejected():
    session = AsyncMock()
    session.scalar.return_value = 0
    session.execute.side_effect = [
        Mock(one=lambda: (0, None)),
        Mock(all=lambda: []),
        Mock(all=lambda: [(None, 1)]),
    ]

    with pytest.raises(ValueError, match="Stored source failure reason is missing"):
        await subscription_diagnostics(session, now=datetime(2026, 10, 2, tzinfo=UTC))

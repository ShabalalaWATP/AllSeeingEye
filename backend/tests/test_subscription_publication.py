"""A completed edition advances only compatible, actually covered time."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ase.container.subscription_publication import _advance_lineage
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
)

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


class Ledger:
    def __init__(self) -> None:
        self.lineage = None
        self.by_version = {}

    async def get_lineage(self, _subscription_id):
        return self.lineage

    async def get_by_version(self, version_id):
        return self.by_version.get(version_id)

    async def save_lineage(self, lineage, *, expected_revision):
        if expected_revision != (self.lineage.revision if self.lineage else None):
            return None
        self.lineage = lineage
        return lineage


def edition(subscription_id, start, end):
    requested = ObservationInterval(start, end)
    return SubscriptionEdition(
        id=uuid4(),
        subscription_id=subscription_id,
        trigger=EditionTrigger.SCHEDULED,
        due_at_utc=end,
        request_uuid=None,
        frozen_revision=1,
        requested=requested,
        effective_intervals=(requested,),
        gaps=(),
        compatibility_fingerprint="a" * 64,
        baseline_version_id=None,
        workflow=EditionWorkflow.COMPLETED,
        report_quality=EditionQuality.READY,
        coverage=EditionCoverage.COMPLETE_FOR_PLAN,
        created_at=NOW,
        updated_at=NOW,
        job_id=uuid4(),
        report_id=uuid4(),
        version_id=uuid4(),
    )


async def test_out_of_order_completion_preserves_latest_baseline_and_fills_gap():
    ledger = Ledger()
    subscription_id = uuid4()
    first = edition(subscription_id, NOW, NOW + timedelta(days=1))
    latest = edition(subscription_id, NOW + timedelta(days=2), NOW + timedelta(days=3))
    middle = edition(subscription_id, NOW + timedelta(days=1), NOW + timedelta(days=2))
    ledger.by_version = {row.version_id: row for row in (first, latest, middle)}

    await _advance_lineage(ledger, first, NOW)
    assert ledger.lineage.complete_cutoff == first.requested.end
    await _advance_lineage(ledger, latest, NOW)
    assert ledger.lineage.complete_cutoff == first.requested.end
    assert ledger.lineage.analytical_baseline_version_id == latest.version_id
    await _advance_lineage(ledger, middle, NOW)
    assert ledger.lineage.complete_cutoff == latest.requested.end
    assert ledger.lineage.analytical_baseline_version_id == latest.version_id
    assert ledger.lineage.covered_intervals == (ObservationInterval(NOW, latest.requested.end),)


async def test_a_report_with_unsearched_dates_does_not_advance_coverage():
    ledger = Ledger()
    row = edition(uuid4(), NOW, NOW + timedelta(days=1))
    row = replace(
        row,
        effective_intervals=(ObservationInterval(NOW, NOW + timedelta(hours=6)),),
        gaps=(ObservationInterval(NOW + timedelta(hours=6), row.requested.end),),
    )
    await _advance_lineage(ledger, row, NOW)
    assert ledger.lineage is None

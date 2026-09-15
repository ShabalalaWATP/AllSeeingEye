"""Substantive changes start a fresh lineage and since-last-success windows stay bounded."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ase.container.subscription_baseline_control import _save_analytical_lineage
from ase.container.subscription_publication import _advance_lineage
from ase.domain.errors import Conflict
from ase.domain.research_scope import validate_research_interval
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    ObservationInterval,
    SubscriptionLineage,
)
from ase.domain.subscription_recurrence import MAX_LOOKBACK, WindowPolicy, requested_window
from test_subscription_publication import NOW, Ledger, edition

OLD, NEW = "a" * 64, "b" * 64


class RevisionLedger(Ledger):
    def __init__(self, latest_fingerprint: str) -> None:
        super().__init__()
        self.latest_fingerprint = latest_fingerprint

    async def latest_revision(self, _subscription_id):
        return SimpleNamespace(compatibility_fingerprint=self.latest_fingerprint)


def _old_lineage(subscription_id) -> SubscriptionLineage:
    covered = ObservationInterval(NOW - timedelta(days=3), NOW)
    return SubscriptionLineage(
        subscription_id=subscription_id,
        compatibility_fingerprint=OLD,
        analytical_baseline_version_id=uuid4(),
        covered_intervals=(covered,),
        complete_cutoff=NOW,
        updated_at=NOW,
        revision=4,
    )


async def test_complete_edition_after_substantive_edit_replaces_lineage() -> None:
    ledger = RevisionLedger(NEW)
    subscription_id = uuid4()
    ledger.lineage = _old_lineage(subscription_id)
    changed = replace(
        edition(subscription_id, NOW + timedelta(days=1), NOW + timedelta(days=2)),
        compatibility_fingerprint=NEW,
    )
    later = NOW + timedelta(days=2)
    await _advance_lineage(ledger, changed, later)
    assert ledger.lineage == SubscriptionLineage(
        subscription_id=subscription_id,
        compatibility_fingerprint=NEW,
        analytical_baseline_version_id=changed.version_id,
        covered_intervals=(changed.requested,),
        complete_cutoff=changed.requested.end,
        updated_at=later,
        revision=5,
    )


async def test_stale_revision_completion_keeps_current_lineage() -> None:
    ledger = RevisionLedger(OLD)
    subscription_id = uuid4()
    ledger.lineage = replace(_old_lineage(subscription_id), compatibility_fingerprint=OLD)
    stale = replace(
        edition(subscription_id, NOW + timedelta(days=1), NOW + timedelta(days=2)),
        compatibility_fingerprint=NEW,
    )
    before = ledger.lineage
    await _advance_lineage(ledger, stale, NOW + timedelta(days=2))
    assert ledger.lineage == before


async def test_accepting_baseline_after_substantive_edit_starts_fresh_lineage() -> None:
    ledger = RevisionLedger(NEW)
    subscription_id = uuid4()
    ledger.lineage = _old_lineage(subscription_id)
    partial = replace(
        edition(subscription_id, NOW + timedelta(days=1), NOW + timedelta(days=2)),
        compatibility_fingerprint=NEW,
        report_quality=EditionQuality.NEEDS_REVIEW,
        coverage=EditionCoverage.PARTIAL,
    )
    later = NOW + timedelta(days=2)
    saved, changed = await _save_analytical_lineage(ledger, partial, later)  # type: ignore[arg-type]
    assert changed is True
    assert saved.compatibility_fingerprint == NEW
    assert saved.analytical_baseline_version_id == partial.version_id
    assert (saved.covered_intervals, saved.complete_cutoff) == ((), None)
    assert saved.revision == 5
    accepted = replace(partial, accepted_as_baseline=True)
    assert await _save_analytical_lineage(ledger, accepted, later) == (saved, False)  # type: ignore[arg-type]
    ledger.lineage = replace(saved, compatibility_fingerprint=OLD)
    with pytest.raises(Conflict):
        await _save_analytical_lineage(ledger, accepted, later)  # type: ignore[arg-type]


def test_since_last_success_window_is_capped_at_the_research_lookback() -> None:
    due = datetime(2029, 1, 1, 6, tzinfo=UTC)
    cutoff = due - timedelta(days=800)
    window = requested_window(
        WindowPolicy.SINCE_LAST_SUCCESS,
        due,
        timedelta(days=1),
        compatible_complete_cutoff=cutoff,
    )
    assert window.interval == ObservationInterval(due - MAX_LOOKBACK, due)
    assert window.overlap == timedelta()
    validate_research_interval(window.interval.start, window.interval.end)
    recent = requested_window(
        WindowPolicy.SINCE_LAST_SUCCESS,
        due,
        timedelta(days=1),
        compatible_complete_cutoff=due - timedelta(hours=12),
    )
    assert recent.interval == ObservationInterval(due - timedelta(hours=15), due)

"""Recorded-time project research can freeze the long interval its boundary accepts."""

import json
from datetime import timedelta

import pytest

from ase.application.report_jobs.snapshots import freeze_job, restore_job
from ase.application.reports.request import ReportRequest
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchMode
from feeds_helpers import NOW
from report_job_snapshot_helpers import fixture_job, fixture_routing, private_store


def _request(days: int, basis: EvidenceTimeBasis | None) -> ReportRequest:
    return ReportRequest(
        "ask",
        question="Which projects were recorded?",
        research_mode=ResearchMode.QUICK,
        research_since=NOW - timedelta(days=days),
        research_until=NOW,
        research_time_basis=basis,
    )


def test_recorded_time_ten_year_window_round_trips() -> None:
    job = fixture_job(_request(3650, EvidenceTimeBasis.RECORDED))
    frozen = freeze_job(job, fixture_routing(job), {}, private_store)
    restored = restore_job(json.loads(json.dumps(frozen)), job.actor, job.profile)
    assert restored.window == timedelta(days=3650)
    assert restored.period_from == job.period_from and restored.period_to == job.period_to


def test_non_recorded_window_keeps_the_live_research_limit() -> None:
    job = fixture_job(_request(2, None))
    frozen = freeze_job(job, fixture_routing(job), {}, private_store)
    tampered = {
        **frozen,
        "window_seconds": 731 * 86400,
        "period_from": (NOW - timedelta(days=731)).isoformat(),
    }
    with pytest.raises(ValueError):
        restore_job(tampered, job.actor, job.profile)

"""Audit duration and integrity checks use fake time; they are not live 24-hour evidence."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ase.adapters.feeds.roster_probe import ProbeResult
from ase.adapters.feeds.rss_seeds import NATIVE_SEEDS
from ase.container import native_feed_audit as audit_module
from feeds_helpers import NOW, FakeClock, make_event


class Probe:
    closed = False

    def __init__(self, clock, seeds):
        self.clock, self.seeds = clock, seeds

    async def fetch(self, seed):
        event = replace(
            make_event(seed.spec.id),
            language=seed.spec.language,
            tags=frozenset({"translate_on_demand"}),
        )
        return ProbeResult(seed.spec.id, seed.spec.url, NOW, 200, 1, NOW), [event]

    async def aclose(self):
        self.closed = True


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.setattr(audit_module, "RosterProbe", Probe)
    monkeypatch.setattr(audit_module, "SystemClock", lambda: FakeClock(NOW))
    elapsed = [0.0]
    monkeypatch.setattr(audit_module, "time", SimpleNamespace(monotonic=lambda: elapsed[0]))
    return audit_module.NativeFeedAudit(), elapsed


async def test_audit_runs_real_queue_but_never_calls_a_model_and_deduplicates(audit):
    run, elapsed = audit
    await run.sample()
    elapsed[0] = 1800
    await run.sample()
    report = run.report(finished=True)
    assert report["distinct_item_ids"] == 15
    assert report["on_demand_item_observations"] == 30
    assert report["unexpected_automatic_translation_attempts"] == 0
    assert report["completed_24_hours"] is False
    assert "Fixture title" not in json.dumps(report, default=str)


async def test_complete_requires_all_49_real_time_rounds_and_clean_state(audit):
    run, elapsed = audit
    for round_number in range(49):
        elapsed[0] = round_number * 1800
        await run.sample()
    assert run.report(finished=False)["completed_24_hours"] is False
    assert run.report(finished=True)["completed_24_hours"] is True
    run.failures = 1
    assert run.report(finished=True)["completed_24_hours"] is False
    run.failures = 0
    run.identity_capacity_reached = True
    assert run.report(finished=True)["completed_24_hours"] is False
    run.identity_capacity_reached = False
    run.max_round_gap_seconds = 3600
    assert run.report(finished=True)["completed_24_hours"] is False


async def test_elapsed_day_alone_never_counts_as_complete(audit):
    run, elapsed = audit
    await run.sample()
    elapsed[0] = 24 * 60 * 60
    assert run.report(finished=True)["completed_24_hours"] is False


async def test_sentinel_raises_on_unexpected_automatic_translation():
    guard = audit_module.NoAutomaticTranslation()
    with pytest.raises(RuntimeError, match="unexpectedly"):
        await guard.translate([("Title", "fr")])
    assert guard.attempts == 1


def test_audit_refuses_automatic_seeds_before_network_initialisation():
    seed = replace(
        NATIVE_SEEDS[0], options=replace(NATIVE_SEEDS[0].options, translate_on_demand=False)
    )
    with pytest.raises(ValueError, match="on-demand"):
        audit_module.NativeFeedAudit([seed])


async def test_existing_report_is_never_overwritten(tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("Keep me", encoding="utf-8")
    with pytest.raises(FileExistsError):
        await audit_module.observe(path, once=True)
    assert path.read_text("utf-8") == "Keep me"

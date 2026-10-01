"""Pure scorecard aggregation and the service's own admin and window checks."""

from datetime import UTC, datetime

import pytest

from ase.container.research_quality import research_quality
from ase.domain.errors import Forbidden, InvalidRequest
from ase.domain.research_quality import (
    NOT_RECORDED,
    TOP_FINDINGS,
    JobOutcome,
    VersionOutcome,
    build_scorecard,
)

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def _version(**changes):
    values = {
        "status": "ready",
        "template": "intsum",
        "depth": None,
        "connection": None,
        "findings": (),
        "receipts": None,
        "prompt_tokens": None,
        "completion_tokens": None,
    }
    return VersionOutcome(**(values | changes))


def _job(**changes):
    values = {
        "status": "running",
        "template": None,
        "depth": None,
        "model": None,
        "error": None,
        "version_saved": False,
    }
    return JobOutcome(**(values | changes))


def _card(versions=(), jobs=()):
    return build_scorecard(
        generated_at=NOW,
        window_days=30,
        since=NOW,
        versions=(len(versions), versions),
        jobs=(len(jobs), jobs),
        template_labels={"intsum": "Intelligence summary"},
        connection_labels={},
    )


def test_findings_are_ranked_by_versions_and_capped():
    rows = [
        _version(findings=tuple((f"rule{index}", "warning") for index in range(count)))
        for count in range(1, 8)
    ]
    findings = _card(rows).versions.overall.findings
    assert len(findings) == TOP_FINDINGS
    assert findings[0].rule == "rule0" and findings[0].versions == 7


def test_receipts_separate_other_unsuccessful_statuses_and_empty_population():
    receipts = _card(
        [_version(receipts=("timed_out", "failed", "completed")), _version(receipts=())]
    ).versions.overall.receipts
    assert (receipts.attempts, receipts.completed, receipts.other_unsuccessful) == (3, 1, 2)
    assert receipts.versions_with_empty_or_unavailable == 0
    empty = _card()
    assert empty.versions.overall.usage.prompt_tokens_per_version is None
    assert empty.versions.by_template == () and empty.jobs.overall.jobs == 0


def test_labels_are_bounded_and_missing_dimensions_are_not_recorded():
    model = "m" * 300
    card = _card([_version()], [_job(model=model), _job(error="model.timeout", status="failed")])
    assert card.versions.by_template[0].label == "Intelligence summary"
    assert card.versions.by_depth[0].key == NOT_RECORDED
    assert card.versions.by_depth[0].label == "Not recorded"
    labels = {row.key: row.label for row in card.jobs.by_model}
    assert len(labels[model]) == 120 and labels[model].endswith("...")
    assert card.jobs.overall.running == 1 and card.jobs.overall.failed_without_version == 1


async def test_the_service_checks_the_role_and_window_itself(container, admin, user):
    async with container.session_factory() as session:
        service = research_quality(container, session)
        with pytest.raises(InvalidRequest):
            await service.scorecard(admin, 45)
        with pytest.raises(Forbidden):
            await service.scorecard(user, 90)
